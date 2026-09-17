"""Subfinder tool wrapper."""

from typing import List, Optional
from pathlib import Path

from .base import ToolWrapper
from ..utils import CommandResult


class SubfinderWrapper(ToolWrapper):
    """Wrapper for subfinder - passive subdomain enumeration."""

    @property
    def name(self) -> str:
        return "subfinder"

    def get_version_args(self) -> List[str]:
        return ["-version"]

    async def enumerate(
        self,
        domains: List[str],
        output: Optional[Path] = None,
        silent: bool = True,
        timeout: int = 300,
        **kwargs
    ) -> CommandResult:
        """Run subfinder enumeration."""
        args = []
        if silent:
            args.append("-silent")
        if output:
            args.extend(["-o", str(output)])

        # Add domains via stdin or -d
        if len(domains) == 1:
            args.extend(["-d", domains[0]])
        else:
            # Multiple domains via stdin
            input_data = "\n".join(domains)
            return await self.run(args, input_data=input_data, timeout=timeout)

        return await self.run(args, timeout=timeout)

    async def enumerate_stdin(
        self,
        domains_input: str,
        output: Optional[Path] = None,
        silent: bool = True,
        timeout: int = 300
    ) -> CommandResult:
        """Run subfinder with domains from stdin."""
        args = []
        if silent:
            args.append("-silent")
        if output:
            args.extend(["-o", str(output)])
        return await self.run(args, input_data=domains_input, timeout=timeout)