"""HTTPX tool wrapper."""

import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from .base import JSONToolWrapper
from ..utils import CommandResult


class HTTPXWrapper(JSONToolWrapper):
    """Wrapper for httpx - HTTP probe and server detection."""

    @property
    def name(self) -> str:
        return "httpx"

    def get_version_args(self) -> List[str]:
        return ["-version"]

    async def probe(
        self,
        input_file: Path,
        output: Optional[Path] = None,
        json_output: bool = True,
        silent: bool = True,
        timeout: int = 30,
        follow_redirects: bool = True,
        **kwargs
    ) -> CommandResult:
        """Probe HTTP servers."""
        args = ["-l", str(input_file)]
        if json_output:
            args.append("-json")
        if silent:
            args.append("-silent")
        if follow_redirects:
            args.append("-follow-redirects")
        if output:
            args.extend(["-o", str(output)])

        return await self.run(args, timeout=timeout)

    async def probe_stdin(
        self,
        input_data: str,
        output: Optional[Path] = None,
        json_output: bool = True,
        timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """Probe from stdin."""
        args = []
        if json_output:
            args.append("-json")
        if output:
            args.extend(["-o", str(output)])
        args.append("-follow-redirects")
        return await self.run_json(args, input_data=input_data, timeout=timeout)

    def extract_urls(self, json_output: List[Dict[str, Any]]) -> List[str]:
        """Extract URLs from httpx JSON output."""
        urls = []
        for entry in json_output:
            if "url" in entry:
                urls.append(entry["url"])
        return urls

    def extract_hostports(self, json_output: List[Dict[str, Any]]) -> List[str]:
        """Extract host:port from httpx JSON output."""
        hostports = []
        for entry in json_output:
            if "host" in entry and "port" in entry:
                hostports.append(f"{entry['host']}:{entry['port']}")
        return hostports