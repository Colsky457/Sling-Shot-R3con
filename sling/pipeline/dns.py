"""DNS enumeration pipeline step."""

from pathlib import Path
from typing import List

from ..pipeline.base import PipelineStep, ScanContext, StepResult
from ..tools import (
    SubfinderWrapper,
    ShuffleDNSWrapper,
    PureDNSWrapper,
    DNSXWrapper,
)
from ..config import Config
from ..state import StateManager
from ..logging import get_logger

logger = get_logger(__name__)


class DNSStep(PipelineStep):
    """DNS enumeration and resolution step."""

    name = "dns"
    dependencies = []
    max_retries = 2

    def __init__(self, config: Config, state: StateManager):
        self.config = config
        self.state = state
        self.subfinder = SubfinderWrapper(config.tools.subfinder, config.dns.passive.timeout)
        self.shuffledns = ShuffleDNSWrapper(config.tools.shuffledns, config.dns.active.timeout)
        self.puredns = PureDNSWrapper(config.tools.puredns, config.dns.resolution.timeout)
        self.dnsx = DNSXWrapper(config.tools.dnsx, config.dns.resolution.timeout)

    async def execute(self, context: ScanContext) -> StepResult:
        """Execute DNS enumeration pipeline."""
        scan_dir = context.scan_dir
        domain = context.domain
        output_paths = []
        artifacts = {}

        # Step 1: Passive enumeration with subfinder
        if self.config.dns.passive.enabled:
            logger.info("dns_passive_start", domain=domain)
            subs_file = scan_dir / "subs_passive.txt"
            result = await self.subfinder.enumerate_stdin(
                domain,
                output=subs_file,
                silent=True,
                timeout=self.config.dns.passive.timeout
            )
            if result.returncode == 0:
                output_paths.append(subs_file)
                count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
                artifacts["subdomains_passive"] = count
                logger.info("dns_passive_complete", count=count)
            else:
                logger.warning("dns_passive_failed", error=result.stderr)

        # Step 2: Active bruteforce with shuffledns
        if self.config.dns.active.enabled:
            logger.info("dns_active_start", domain=domain)
            subs_active_file = scan_dir / "subs_active.txt"
            result = await self.shuffledns.bruteforce(
                domain,
                self.config.wordlists.subdomains,
                self.config.wordlists.resolvers,
                output=subs_active_file,
                silent=True,
                timeout=self.config.dns.active.timeout
            )
            if result.returncode == 0:
                output_paths.append(subs_active_file)
                count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
                artifacts["subdomains_active"] = count
                logger.info("dns_active_complete", count=count)
            else:
                logger.warning("dns_active_failed", error=result.stderr)

        # Combine subdomains
        all_subs_file = scan_dir / "subs.txt"
        await self._combine_subdomains(scan_dir, all_subs_file)
        total_subs = await self._count_lines(all_subs_file)
        artifacts["subdomains_total"] = total_subs
        output_paths.append(all_subs_file)

        # Step 3: Resolution with puredns
        if self.config.dns.resolution.enabled and total_subs > 0:
            logger.info("dns_resolution_start", count=total_subs)
            resolved_file = scan_dir / "resolved.txt"
            result = await self.puredns.resolve(
                all_subs_file,
                self.config.wordlists.resolvers,
                output=resolved_file,
                timeout=self.config.dns.resolution.timeout
            )
            if result.returncode == 0:
                output_paths.append(resolved_file)
                resolved_count = await self._count_lines(resolved_file)
                artifacts["subdomains_resolved"] = resolved_count
                logger.info("dns_resolution_complete", count=resolved_count)

                # Step 4: DNSX for detailed records
                logger.info("dnsx_start", count=resolved_count)
                dns_json = scan_dir / "dns.json"
                result = await self.dnsx.query(
                    resolved_file,
                    output=dns_json,
                    json_output=True,
                    timeout=self.config.dns.resolution.timeout
                )
                if result.returncode == 0:
                    output_paths.append(dns_json)
                    # Extract IPs
                    ips_file = scan_dir / "ips.txt"
                    dns_data = await self._parse_dnsx_json(dns_json)
                    ips = self.dnsx.parse_a_records(dns_data)
                    await self._write_lines(ips_file, ips)
                    output_paths.append(ips_file)
                    artifacts["ips"] = len(ips)
                    logger.info("dnsx_complete", ips=len(ips))
                else:
                    logger.warning("dnsx_failed", error=result.stderr)
            else:
                logger.warning("dns_resolution_failed", error=result.stderr)

        return StepResult(
            success=True,
            output_paths=output_paths,
            artifacts=artifacts,
            metadata={"domain": domain}
        )

    async def _combine_subdomains(self, scan_dir: Path, output: Path) -> None:
        """Combine passive and active subdomain results."""
        import asyncio
        passive = scan_dir / "subs_passive.txt"
        active = scan_dir / "subs_active.txt"

        lines = set()
        for f in [passive, active]:
            if f.exists():
                content = await asyncio.to_thread(f.read_text, encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if line:
                        lines.add(line)

        await asyncio.to_thread(output.write_text, "\n".join(sorted(lines)) + "\n")

    async def _count_lines(self, file: Path) -> int:
        """Count non-empty lines in file."""
        if not file.exists():
            return 0
        import asyncio
        content = await asyncio.to_thread(file.read_text, encoding="utf-8", errors="ignore")
        return sum(1 for line in content.splitlines() if line.strip())

    async def _write_lines(self, file: Path, lines: List[str]) -> None:
        """Write lines to file."""
        import asyncio
        await asyncio.to_thread(file.write_text, "\n".join(lines) + "\n")

    async def _parse_dnsx_json(self, file: Path) -> List[dict]:
        """Parse dnsx JSON output."""
        import asyncio
        import json
        content = await asyncio.to_thread(file.read_text, encoding="utf-8", errors="ignore")
        results = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return results

    def get_output_paths(self, context: ScanContext) -> List[Path]:
        """Get expected output paths."""
        scan_dir = context.scan_dir
        return [
            scan_dir / "subs.txt",
            scan_dir / "resolved.txt",
            scan_dir / "dns.json",
            scan_dir / "ips.txt",
        ]