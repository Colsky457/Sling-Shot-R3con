"""PureDNS tool wrapper."""

from typing import Optional
from pathlib import Path

from .base import ToolWrapper
from ..utils import CommandResult


class PureDNSWrapper(ToolWrapper):
    """Wrapper for puredns - DNS resolution and validation."""

    @property
    def name(self) -> str:
        return "puredns"

    def get_version_args(self) -> List[str]:
        return ["version"]

    async def resolve(
        self,
        subdomains_file: Path,
        resolvers: Path,
        output: Optional[Path] = None,
        write_wildcards: Optional[Path] = None,
        timeout: int = 300
    ) -> CommandResult:
        """Resolve subdomains from file."""
        args = ["resolve", str(subdomains_file), "-r", str(resolvers)]
        if output:
            args.extend(["-w", str(output)])
        if write_wildcards:
            args.extend(["--wildcard", str(write_wildcards)])
        return await self.run(args, timeout=timeout)

    async def bruteforce(
        self,
        domain: str,
        wordlist: Path,
        resolvers: Path,
        output: Optional[Path] = None,
        timeout: int = 600
    ) -> CommandResult:
        """Bruteforce subdomains."""
        args = ["bruteforce", str(wordlist), domain, "-r", str(resolvers)]
        if output:
            args.extend(["-w", str(output)])
        return await self.run(args, timeout=timeout)