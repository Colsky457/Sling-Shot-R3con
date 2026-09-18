"""TEW tool wrapper."""

from typing import Optional, List
from pathlib import Path

from .base import ToolWrapper
from ..utils import CommandResult


class TEWWrapper(ToolWrapper):
    """Wrapper for tew - host:port extraction from DNS."""

    @property
    def name(self) -> str:
        return "tew"

    def get_version_args(self) -> List[str]:
        return ["-version"]

    async def extract(
        self,
        input_file: Path,
        dnsx_file: Path,
        output: Optional[Path] = None,
        vhost: bool = True,
        timeout: int = 60
    ) -> CommandResult:
        """Extract host:port from naabu output using dnsx data."""
        args = [
            "-l", str(input_file),
            "-dnsx", str(dnsx_file),
        ]
        if vhost:
            args.append("--vhost")
        if output:
            args.extend(["-o", str(output)])

        return await self.run(args, timeout=timeout)