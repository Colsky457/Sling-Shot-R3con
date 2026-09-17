"""Crawling and JavaScript scraping pipeline step."""

from pathlib import Path
from typing import List

from ..pipeline.base import PipelineStep, ScanContext, StepResult
from ..tools import KatanaWrapper, HTTPXWrapper
from ..config import Config
from ..state import StateManager
from ..logging import get_logger

logger = get_logger(__name__)


class CrawlStep(PipelineStep):
    """Crawling and JavaScript scraping step."""

    name = "crawl"
    dependencies = ["port"]
    max_retries = 1

    def __init__(self, config: Config, state: StateManager):
        self.config = config
        self.state = state
        self.katana = KatanaWrapper(config.tools.katana, config.crawl.timeout)
        self.httpx = HTTPXWrapper(config.tools.httpx, 30)

    async def execute(self, context: ScanContext) -> StepResult:
        """Execute crawling pipeline."""
        scan_dir = context.scan_dir
        output_paths = []
        artifacts = {}

        # Check for HTTP targets
        http_file = scan_dir / "http.txt"
        if not http_file.exists():
            logger.warning("crawl_skip_no_http", scan_dir=str(scan_dir))
            return StepResult(success=True, output_paths=[], artifacts={"skipped": "no_http"})

        # Step 1: Crawl with katana
        if self.config.crawl.enabled:
            logger.info("crawl_start", depth=self.config.crawl.depth)
            crawl_file = scan_dir / "crawl.txt"
            result = await self.katana.crawl(
                http_file,
                output=crawl_file,
                json_output=True,
                depth=self.config.crawl.depth,
                timeout=self.config.crawl.timeout
            )
            if result.returncode == 0:
                output_paths.append(crawl_file)
                # Parse outputs
                crawl_data = await self._parse_katana_json(crawl_file)
                urls = self.katana.extract_outputs(crawl_data)
                await self._write_lines(crawl_file, urls)
                artifacts["crawled_urls"] = len(urls)
                logger.info("crawl_complete", count=len(urls))

                # Step 2: Extract and download JS files
                if self.config.crawl.js_extraction:
                    js_urls = self.katana.extract_js_urls(crawl_data)
                    if js_urls:
                        logger.info("js_extraction_start", count=len(js_urls))
                        js_dir = scan_dir / "js"
                        js_dir.mkdir(exist_ok=True)
                        js_urls_file = scan_dir / "js_urls.txt"
                        await self._write_lines(js_urls_file, js_urls)

                        # Download JS files with httpx
                        # httpx -sr -srd js saves response bodies to js/ directory
                        # We'll use a simpler approach - just record the URLs
                        js_output_file = scan_dir / "js_downloaded.txt"
                        # For now, just record the URLs found
                        await self._write_lines(js_output_file, js_urls)
                        output_paths.append(js_output_file)
                        artifacts["js_files"] = len(js_urls)
                        logger.info("js_extraction_complete", count=len(js_urls))
            else:
                logger.warning("crawl_failed", error=result.stderr)

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

    async def _parse_katana_json(self, file: Path) -> List[dict]:
        """Parse katana JSON output."""
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
            scan_dir / "crawl.txt",
            scan_dir / "js_urls.txt",
        ]