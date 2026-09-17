"""Naabu tool wrapper."""

from typing import List, Optional
from pathlib import Path

from .base import ToolWrapper
from ..utils import CommandResult


class NaabuWrapper(ToolWrapper):
    """Wrapper for naabu - port scanner."""

    @property
    def name(self) -> str:
        return "naabu"

    def get_version_args(self) -> List[str]:
        return ["-version"]

    async def scan(
        self,
        input_file: Path,
        ports: str,
        rate: int = 1000,
        output: Optional[Path] = None,
        silent: bool = True,
        timeout: int = 600,
        **kwargs
    ) -> CommandResult:
        """Run naabu port scan."""
        args = [
            "-iL", str(input_file),
            "-p", ports,
            "-rate", str(rate),
        ]
        if silent:
            args.append("-silent")
        if output:
            args.extend(["-o", str(output)])

        return await self.run(args, timeout=timeout)

    async def scan_hosts(
        self,
        hosts: List[str],
        ports: str,
        rate: int = 1000,
        output: Optional[Path] = None,
        silent: bool = True,
        timeout: int = 600
    ) -> CommandResult:
        """Scan list of hosts."""
        args = [
            "-host", ",".join(hosts),
            "-p", ports,
            "-rate", str(rate),
        ]
        if silent:
            args.append("-silent")
        if output:
            args.extend(["-o", str(output)])

        return await self.run(args, timeout=timeout)