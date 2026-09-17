"""Katana tool wrapper."""

import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from .base import JSONToolWrapper
from ..utils import CommandResult


class KatanaWrapper(JSONToolWrapper):
    """Wrapper for katana - web crawler."""

    @property
    def name(self) -> str:
        return "katana"

    def get_version_args(self) -> List[str]:
        return ["-version"]

    async def crawl(
        self,
        input_file: Path,
        output: Optional[Path] = None,
        json_output: bool = True,
        depth: int = 2,
        timeout: int = 600,
        **kwargs
    ) -> CommandResult:
        """Crawl URLs from file."""
        args = [
            "-list", str(input_file),
            "-depth", str(depth),
        ]
        if json_output:
            args.append("-json")
        if output:
            args.extend(["-o", str(output)])

        return await self.run(args, timeout=timeout)

    async def crawl_stdin(
        self,
        input_data: str,
        output: Optional[Path] = None,
        json_output: bool = True,
        depth: int = 2,
        timeout: int = 600
    ) -> List[Dict[str, Any]]:
        """Crawl from stdin."""
        args = ["-depth", str(depth)]
        if json_output:
            args.append("-json")
        if output:
            args.extend(["-o", str(output)])
        return await self.run_json(args, input_data=input_data, timeout=timeout)

    def extract_outputs(self, json_output: List[Dict[str, Any]]) -> List[str]:
        """Extract output URLs from katana JSON output."""
        urls = []
        for entry in json_output:
            if "output" in entry:
                urls.append(entry["output"])
        return urls

    def extract_js_urls(self, json_output: List[Dict[str, Any]]) -> List[str]:
        """Extract JavaScript URLs from katana JSON output."""
        js_urls = []
        for entry in json_output:
            if "output" in entry and entry["output"].endswith(".js"):
                js_urls.append(entry["output"])
        return js_urls