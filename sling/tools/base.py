"""Base tool wrapper class."""

import asyncio
import shlex
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..utils import run_command, CommandResult
from ..logging import get_logger

logger = get_logger(__name__)


class ToolWrapper(ABC):
    """Base class for external tool wrappers."""

    def __init__(self, tool_path: str, timeout: int = 300):
        self.tool_path = tool_path
        self.timeout = timeout
        self._available: Optional[bool] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @abstractmethod
    def get_version_args(self) -> List[str]:
        """Arguments to get tool version."""
        pass

    async def check_available(self) -> bool:
        """Check if tool is available and executable."""
        if self._available is not None:
            return self._available

        try:
            result = await run_command(
                [self.tool_path] + self.get_version_args(),
                timeout=10
            )
            self._available = result.returncode == 0
            if self._available:
                logger.debug("tool_available", tool=self.name, path=self.tool_path)
            else:
                logger.warning("tool_not_available", tool=self.name, path=self.tool_path)
        except Exception as e:
            logger.warning("tool_check_failed", tool=self.name, error=str(e))
            self._available = False
        return self._available

    async def run(
        self,
        args: List[str],
        input_data: Optional[str] = None,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None
    ) -> CommandResult:
        """Run the tool with given arguments."""
        if not await self.check_available():
            raise RuntimeError(f"Tool '{self.name}' not available at {self.tool_path}")

        cmd = [self.tool_path] + args
        return await run_command(cmd, timeout=timeout or self.timeout, cwd=cwd, input_data=input_data)

    def build_args(self, **kwargs) -> List[str]:
        """Build command line arguments from keyword arguments."""
        args = []
        for key, value in kwargs.items():
            if value is None or value is False:
                continue
            if value is True:
                args.append(f"--{key.replace('_', '-')}")
            elif isinstance(value, list):
                for v in value:
                    args.extend([f"--{key.replace('_', '-')}", str(v)])
            else:
                args.extend([f"--{key.replace('_', '-')}", str(value)])
        return args


class JSONToolWrapper(ToolWrapper):
    """Wrapper for tools that output JSON."""

    async def run_json(
        self,
        args: List[str],
        input_data: Optional[str] = None,
        cwd: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """Run tool and parse JSON output line by line."""
        result = await self.run(args, input_data, cwd)
        if result.returncode != 0:
            raise RuntimeError(f"{self.name} failed: {result.stderr}")

        objects = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    import json
                    objects.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("json_parse_failed", tool=self.name, line=line[:100])
        return objects