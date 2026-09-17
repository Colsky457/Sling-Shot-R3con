"""ShuffleDNS tool wrapper."""

from typing import List, Optional
from pathlib import Path

from .base import ToolWrapper
from ..utils import CommandResult


class ShuffleDNSWrapper(ToolWrapper):
    """Wrapper for shuffledns - active subdomain bruteforce."""

    @property
    def name(self) -> str:
        return "shuffledns"

    def get_version_args(self) -> List[str]:
        return ["-version"]

    async def bruteforce(
        self,
        domain: str,
        wordlist: Path,
        resolvers: Path,
        output: Optional[Path] = None,
        silent: bool = True,
        timeout: int = 600,
        **kwargs
    ) -> CommandResult:
        """Run shuffledns bruteforce."""
        args = [
            "-d", domain,
            "-w", str(wordlist),
            "-r", str(resolvers),
        ]
        if silent:
            args.append("-silent")
        if output:
            args.extend(["-o", str(output)])

        return await self.run(args, timeout=timeout)

    async def resolve(
        self,
        subdomains_input: str,
        resolvers: Path,
        output: Optional[Path] = None,
        silent: bool = True,
        timeout: int = 300
    ) -> CommandResult:
        """Resolve subdomains from stdin."""
        args = ["-r", str(resolvers), "-mode", "resolve"]
        if silent:
            args.append("-silent")
        if output:
            args.extend(["-o", str(output)])
        return await self.run(args, input_data=subdomains_input, timeout=timeout)