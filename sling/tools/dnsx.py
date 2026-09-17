"""DNSX tool wrapper."""

import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from .base import JSONToolWrapper
from ..utils import CommandResult


class DNSXWrapper(JSONToolWrapper):
    """Wrapper for dnsx - DNS toolkit."""

    @property
    def name(self) -> str:
        return "dnsx"

    def get_version_args(self) -> List[str]:
        return ["-version"]

    async def query(
        self,
        input_file: Path,
        output: Optional[Path] = None,
        json_output: bool = True,
        a: bool = True,
        aaaa: bool = True,
        cname: bool = True,
        ns: bool = True,
        mx: bool = True,
        txt: bool = True,
        timeout: int = 300,
        **kwargs
    ) -> CommandResult:
        """Run dnsx queries."""
        args = ["-l", str(input_file)]
        if json_output:
            args.append("-json")
        if output:
            args.extend(["-o", str(output)])
        if a:
            args.append("-a")
        if aaaa:
            args.append("-aaaa")
        if cname:
            args.append("-cname")
        if ns:
            args.append("-ns")
        if mx:
            args.append("-mx")
        if txt:
            args.append("-txt")

        return await self.run(args, timeout=timeout)

    async def query_stdin(
        self,
        input_data: str,
        output: Optional[Path] = None,
        json_output: bool = True,
        timeout: int = 300
    ) -> List[Dict[str, Any]]:
        """Run dnsx with input from stdin."""
        args = []
        if json_output:
            args.append("-json")
        if output:
            args.extend(["-o", str(output)])
        args.extend(["-a", "-aaaa", "-cname", "-ns", "-mx", "-txt"])
        return await self.run_json(args, input_data=input_data, timeout=timeout)

    def parse_a_records(self, json_output: List[Dict[str, Any]]) -> List[str]:
        """Extract A records from dnsx JSON output."""
        ips = []
        for entry in json_output:
            if "a" in entry:
                ips.extend(entry["a"])
        return list(set(ips))