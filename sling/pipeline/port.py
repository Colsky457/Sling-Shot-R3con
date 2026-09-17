"""Port scanning and HTTP discovery pipeline step."""

from pathlib import Path
from typing import List

from ..pipeline.base import PipelineStep, ScanContext, StepResult
from ..tools import NaabuWrapper, TEWWrapper, HTTPXWrapper
from ..config import Config
from ..state import StateManager
from ..utils import resolve_ports
from ..logging import get_logger

logger = get_logger(__name__)


class PortStep(PipelineStep):
    """Port scanning and HTTP discovery step."""

    name = "port"
    dependencies = ["dns"]
    max_retries = 2

    def __init__(self, config: Config, state: StateManager):
        self.config = config
        self.state = state
        self.naabu = NaabuWrapper(config.tools.naabu, config.port.scan.timeout)
        self.tew = TEWWrapper(config.tools.tew, 60)
        self.httpx = HTTPXWrapper(config.tools.httpx, config.port.http_probe.timeout)

    async def execute(self, context: ScanContext) -> StepResult:
        """Execute port scanning and HTTP discovery."""
        scan_dir = context.scan_dir
        output_paths = []
        artifacts = {}

        # Check for IPs from DNS step
        ips_file = scan_dir / "ips.txt"
        if not ips_file.exists():
            logger.warning("port_skip_no_ips", scan_dir=str(scan_dir))
            return StepResult(success=True, output_paths=[], artifacts={"skipped": "no_ips"})

        # Step 1: Port scan with naabu
        if self.config.port.scan.enabled:
            logger.info("port_scan_start")
            ports_spec = self.config.port.scan.ports
            ports_list = resolve_ports(ports_spec)
            ports_str = ",".join(map(str, ports_list))

            ports_file = scan_dir / "ports.txt"
            result = await self.naabu.scan(
                ips_file,
                ports_str,
                rate=self.config.port.scan.rate,
                output=ports_file,
                silent=True,
                timeout=self.config.port.scan.timeout
            )
            if result.returncode == 0:
                output_paths.append(ports_file)
                port_count = await self._count_lines(ports_file)
                artifacts["ports"] = port_count
                logger.info("port_scan_complete", count=port_count)
            else:
                logger.warning("port_scan_failed", error=result.stderr)
                return StepResult(success=False, error=result.stderr, output_paths=output_paths)

        # Step 2: Extract host:port with tew
        ports_file = scan_dir / "ports.txt"
        dns_json = scan_dir / "dns.json"
        hostport_file = scan_dir / "hostport.txt"

        if ports_file.exists() and dns_json.exists():
            logger.info("tew_start")
            result = await self.tew.extract(
                ports_file,
                dns_json,
                output=hostport_file,
                vhost=True,
                timeout=60
            )
            if result.returncode == 0:
                output_paths.append(hostport_file)
                hp_count = await self._count_lines(hostport_file)
                artifacts["hostports"] = hp_count
                logger.info("tew_complete", count=hp_count)
            else:
                logger.warning("tew_failed", error=result.stderr)

        # Step 3: HTTP probe with httpx
        if self.config.port.http_probe.enabled and hostport_file.exists():
            logger.info("httpx_start")
            http_json = scan_dir / "http.json"
            result = await self.httpx.probe(
                hostport_file,
                output=http_json,
                json_output=True,
                silent=True,
                timeout=self.config.port.http_probe.timeout
            )
            if result.returncode == 0:
                output_paths.append(http_json)
                # Extract URLs
                http_txt = scan_dir / "http.txt"
                http_data = await self._parse_httpx_json(http_json)
                urls = self.httpx.extract_urls(http_data)
                await self._write_lines(http_txt, urls)
                output_paths.append(http_txt)
                artifacts["http_services"] = len(urls)
                logger.info("httpx_complete", count=len(urls))
            else:
                logger.warning("httpx_failed", error=result.stderr)

        return StepResult(
            success=True,
            output_paths=output_paths,
            artifacts=artifacts
        )

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
        await asyncio.to_thread(file.write_text, "\n".join(sorted(set(lines))) + "\n")

    async def _parse_httpx_json(self, file: Path) -> List[dict]:
        """Parse httpx JSON output."""
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
            scan_dir / "ports.txt",
            scan_dir / "hostport.txt",
            scan_dir / "http.json",
            scan_dir / "http.txt",
        ]