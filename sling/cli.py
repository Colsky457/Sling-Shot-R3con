"""CLI entry point for Sling."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import Config
from .state import StateManager, ScanStatus, StepStatus
from .pipeline import PipelineOrchestrator, DNSStep, PortStep, CrawlStep, ScanContext
from .logging import setup_logging, get_logger

logger = get_logger(__name__)
console = Console()


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], verbose: bool):
    """Sling - Automated reconnaissance for bug bounty and pentesting."""
    ctx.ensure_object(dict)
    cfg = Config()
    if config:
        # TODO: Load custom config file
        pass
    if verbose:
        cfg.general.log_level = "DEBUG"
    setup_logging(cfg)
    ctx.obj["config"] = cfg
    ctx.obj["state"] = StateManager(cfg)


@cli.command()
@click.argument("domain")
@click.option("--resume", "-r", is_flag=True, help="Resume interrupted scan")
@click.option("--dry-run", is_flag=True, help="Show what would be executed without running")
@click.pass_context
def scan(ctx: click.Context, domain: str, resume: bool, dry_run: bool):
    """Start a new scan for the given domain."""
    from .utils.validation import validate_target
    
    if not validate_target(domain):
        console.print(f"[red]Invalid target: {domain}[/red]")
        raise click.Abort()

    config: Config = ctx.obj["config"]
    state: StateManager = ctx.obj["state"]

    # Create or resume scan
    if resume:
        # Find latest incomplete scan for this domain
        scans = state.get_scan_by_domain(domain)
        incomplete = [s for s in scans if s["status"] in (ScanStatus.RUNNING.value, ScanStatus.PAUSED.value, ScanStatus.FAILED.value)]
        if not incomplete:
            console.print(f"[yellow]No incomplete scan found for {domain}[/yellow]")
            raise click.Abort()
        scan_id = incomplete[0]["id"]
        console.print(f"[cyan]Resuming scan {scan_id} for {domain}[/cyan]")
    else:
        scan_id = state.create_scan(domain)
        console.print(f"[green]Created scan {scan_id} for {domain}[/green]")

    # Create scan directory
    scan_dir = config.general.output_dir / f"{domain}-{scan_id}"
    scan_dir.mkdir(parents=True, exist_ok=True)

    # Initialize pipeline
    steps = [
        DNSStep(config, state),
        PortStep(config, state),
        CrawlStep(config, state),
    ]
    orchestrator = PipelineOrchestrator(steps, config, state)

    context = ScanContext(
        scan_id=scan_id,
        domain=domain,
        scan_dir=scan_dir,
        config=config,
        state=state
    )

    if dry_run:
        console.print("[yellow]DRY RUN - Would execute:[/yellow]")
        for step in steps:
            console.print(f"  - {step.name} (deps: {step.dependencies})")
        return

    # Update scan status
    state.update_scan_status(scan_id, ScanStatus.RUNNING)

    # Run pipeline
    try:
        asyncio.run(orchestrator.execute(context, resume=resume))
        state.update_scan_status(scan_id, ScanStatus.COMPLETED)
        console.print(f"[green]Scan {scan_id} completed successfully![/green]")
        _print_summary(state, scan_id)
    except Exception as e:
        state.update_scan_status(scan_id, ScanStatus.FAILED)
        console.print(f"[red]Scan {scan_id} failed: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument("scan_id")
@click.pass_context
def resume(ctx: click.Context, scan_id: str):
    """Resume a specific scan by ID."""
    config: Config = ctx.obj["config"]
    state: StateManager = ctx.obj["state"]

    scan = state.get_scan(scan_id)
    if not scan:
        console.print(f"[red]Scan {scan_id} not found[/red]")
        raise click.Abort()

    if scan["status"] == ScanStatus.COMPLETED.value:
        console.print(f"[yellow]Scan {scan_id} already completed[/yellow]")
        return

    # Re-run scan command with resume flag
    ctx.invoke(scan, domain=scan["domain"], resume=True)


@cli.command()
@click.pass_context
def list(ctx: click.Context):
    """List all scans."""
    state: StateManager = ctx.obj["state"]
    scans = state.list_scans()

    table = Table(title="Scans")
    table.add_column("ID", style="cyan")
    table.add_column("Domain", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created", style="dim")
    table.add_column("Current Step")

    for scan in scans:
        status_style = {
            "completed": "green",
            "running": "yellow",
            "failed": "red",
            "pending": "blue",
            "paused": "magenta",
        }.get(scan["status"], "white")
        table.add_row(
            scan["id"],
            scan["domain"],
            f"[{status_style}]{scan['status']}[/{status_style}]",
            scan["created_at"],
            scan["current_step"] or "-"
        )

    console.print(table)


@cli.command()
@click.argument("scan_id")
@click.pass_context
def status(ctx: click.Context, scan_id: str):
    """Show detailed status of a scan."""
    state: StateManager = ctx.obj["state"]
    scan = state.get_scan(scan_id)
    
    if not scan:
        console.print(f"[red]Scan {scan_id} not found[/red]")
        raise click.Abort()

    console.print(Panel(f"[bold]Scan {scan_id}[/bold]", subtitle=scan["domain"]))
    console.print(f"Status: [bold]{scan['status']}[/bold]")
    console.print(f"Created: {scan['created_at']}")
    console.print(f"Updated: {scan['updated_at']}")
    console.print(f"Current Step: {scan['current_step'] or 'N/A'}")

    steps = state.get_steps(scan_id)
    if steps:
        table = Table(title="Steps")
        table.add_column("Step", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Started")
        table.add_column("Completed")
        table.add_column("Retries")
        table.add_column("Output")

        for step in steps:
            status_style = {
                "completed": "green",
                "running": "yellow",
                "failed": "red",
                "pending": "blue",
                "skipped": "magenta",
            }.get(step["status"], "white")
            table.add_row(
                step["name"],
                f"[{status_style}]{step['status']}[/{status_style}]",
                step["started_at"] or "-",
                step["completed_at"] or "-",
                str(step["retry_count"]),
                step["output_path"] or "-"
            )
        console.print(table)

    artifacts = state.get_artifacts(scan_id)
    if artifacts:
        table = Table(title="Artifacts")
        table.add_column("Step", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Count", style="yellow")
        table.add_column("Path")

        for art in artifacts:
            table.add_row(art["step_name"], art["type"], str(art["count"]), art["path"])
        console.print(table)


@cli.command()
@click.argument("scan_id")
@click.pass_context
def artifacts(ctx: click.Context, scan_id: str):
    """List artifacts for a scan."""
    state: StateManager = ctx.obj["state"]
    scan = state.get_scan(scan_id)
    
    if not scan:
        console.print(f"[red]Scan {scan_id} not found[/red]")
        raise click.Abort()

    artifacts = state.get_artifacts(scan_id)
    if not artifacts:
        console.print("[yellow]No artifacts found[/yellow]")
        return

    table = Table(title=f"Artifacts for {scan_id}")
    table.add_column("Step", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Count", style="yellow")
    table.add_column("Path")

    for art in artifacts:
        table.add_row(art["step_name"], art["type"], str(art["count"]), art["path"])
    console.print(table)


def _print_summary(state: StateManager, scan_id: str) -> None:
    """Print scan summary."""
    artifacts = state.get_artifacts(scan_id)
    if not artifacts:
        return

    table = Table(title="Scan Summary")
    table.add_column("Type", style="green")
    table.add_column("Count", style="yellow")

    summary = {}
    for art in artifacts:
        summary[art["type"]] = summary.get(art["type"], 0) + art["count"]

    for art_type, count in sorted(summary.items()):
        table.add_row(art_type, str(count))

    console.print(table)


def main():
    """Entry point for console script."""
    cli(obj={})


if __name__ == "__main__":
    main()