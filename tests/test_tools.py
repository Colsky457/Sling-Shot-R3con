"""Tests for tool wrappers."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sling.tools.base import ToolWrapper, CommandResult
from sling.tools.puredns import PureDNSWrapper
from sling.tools.tew import TEWWrapper
from sling.tools.subfinder import SubfinderWrapper
from sling.tools.httpx import HTTPXWrapper
from sling.tools.naabu import NaabuWrapper
from sling.tools.katana import KatanaWrapper


class MockToolWrapper(ToolWrapper):
    """Concrete ToolWrapper for testing base class behavior."""

    @property
    def name(self) -> str:
        return "mocktool"

    def get_version_args(self) -> list:
        return ["--version"]


class TestToolWrapperCheckAvailable:
    """Tests for ToolWrapper.check_available()."""

    @pytest.mark.asyncio
    async def test_check_available_returns_true_on_success(self):
        """Tool should be available when version command returns 0."""
        with patch("sling.tools.base.run_command", new=AsyncMock(return_value=CommandResult(
            returncode=0, stdout="v1.0.0", stderr="", command="mocktool --version"
        ))):
            wrapper = MockToolWrapper("/path/to/mocktool")
            available = await wrapper.check_available()
            assert available is True
            wrapper._available is True

    @pytest.mark.asyncio
    async def test_check_available_returns_false_on_failure(self):
        """Tool should be unavailable when version command returns non-zero."""
        with patch("sling.tools.base.run_command", new=AsyncMock(return_value=CommandResult(
            returncode=1, stdout="", stderr="not found", command="mocktool --version"
        ))):
            wrapper = MockToolWrapper("/path/to/mocktool")
            available = await wrapper.check_available()
            assert available is False

    @pytest.mark.asyncio
    async def test_check_available_returns_false_on_exception(self):
        """Tool should be unavailable when version command raises exception."""
        with patch("sling.tools.base.run_command", new=AsyncMock(side_effect=FileNotFoundError("not found"))):
            wrapper = MockToolWrapper("/path/to/mocktool")
            available = await wrapper.check_available()
            assert available is False

    @pytest.mark.asyncio
    async def test_check_available_cached(self):
        """Check available should cache result and not call run_command twice."""
        run_command_mock = AsyncMock(return_value=CommandResult(
            returncode=0, stdout="v1.0.0", stderr="", command="mocktool --version"
        ))
        with patch("sling.tools.base.run_command", new=run_command_mock):
            wrapper = MockToolWrapper("/path/to/mocktool")
            await wrapper.check_available()
            await wrapper.check_available()
            assert run_command_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_check_available_uses_correct_command(self):
        """Check available should call run_command with tool path and version args."""
        with patch("sling.tools.base.run_command", new=AsyncMock(return_value=CommandResult(
            returncode=0, stdout="", stderr="", command=""
        ))):
            wrapper = PureDNSWrapper("/usr/bin/puredns", 300)
            await wrapper.check_available()
            call_args = run_command_mock = None
            # Access the mock via patch context
            import sling.tools.base as base_module
            original = base_module.run_command
            # We need a different approach - re-run with tracking
        # Re-test with explicit tracking
        tracked_calls = []
        async def tracking_run_command(cmd, **kwargs):
            tracked_calls.append(cmd)
            return CommandResult(returncode=0, stdout="", stderr="", command=" ".join(cmd))

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = PureDNSWrapper("/usr/bin/puredns", 300)
            await wrapper.check_available()
            assert tracked_calls[0][0] == "/usr/bin/puredns"
            assert "-version" in tracked_calls[0]


class TestToolWrapperRun:
    """Tests for ToolWrapper.run()."""

    @pytest.mark.asyncio
    async def test_run_raises_when_tool_unavailable(self):
        """Run should raise RuntimeError when tool is not available."""
        with patch("sling.tools.base.run_command", new=AsyncMock(return_value=CommandResult(
            returncode=1, stdout="", stderr="not found", command=""
        ))):
            wrapper = MockToolWrapper("/path/to/mocktool")
            with pytest.raises(RuntimeError, match="not available"):
                await wrapper.run(["--help"])

    @pytest.mark.asyncio
    async def test_run_calls_run_command_with_correct_args(self):
        """Run should call run_command with tool path plus arguments."""
        tracked_calls = []
        async def tracking_run_command(cmd, **kwargs):
            tracked_calls.append((cmd, kwargs))
            return CommandResult(returncode=0, stdout="output", stderr="", command=" ".join(cmd))

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = MockToolWrapper("/path/to/mocktool")
            wrapper._available = True  # Bypass availability check
            result = await wrapper.run(["--verbose", "--output", "/tmp/out.txt"])
            assert tracked_calls[0][0][0] == "/path/to/mocktool"
            assert "--verbose" in tracked_calls[0][0]
            assert "--output" in tracked_calls[0][0]
            assert "/tmp/out.txt" in tracked_calls[0][0]
            assert result.returncode == 0
            assert result.stdout == "output"

    @pytest.mark.asyncio
    async def test_run_passes_timeout(self):
        """Run should pass timeout to run_command."""
        tracked_kwargs = {}
        async def tracking_run_command(cmd, **kwargs):
            tracked_kwargs.update(kwargs)
            return CommandResult(returncode=0, stdout="", stderr="", command="")

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = MockToolWrapper("/path/to/mocktool", timeout=60)
            wrapper._available = True
            await wrapper.run(["--help"], timeout=120)
            assert tracked_kwargs.get("timeout") == 120

    @pytest.mark.asyncio
    async def test_run_uses_default_timeout(self):
        """Run should use default timeout when not specified."""
        tracked_kwargs = {}
        async def tracking_run_command(cmd, **kwargs):
            tracked_kwargs.update(kwargs)
            return CommandResult(returncode=0, stdout="", stderr="", command="")

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = MockToolWrapper("/path/to/mocktool", timeout=45)
            wrapper._available = True
            await wrapper.run(["--help"])
            assert tracked_kwargs.get("timeout") == 45

    @pytest.mark.asyncio
    async def test_run_with_input_data(self):
        """Run should pass input_data to run_command."""
        tracked_kwargs = {}
        async def tracking_run_command(cmd, **kwargs):
            tracked_kwargs.update(kwargs)
            return CommandResult(returncode=0, stdout="", stderr="", command="")

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = MockToolWrapper("/path/to/mocktool")
            wrapper._available = True
            await wrapper.run(["--help"], input_data="test input")
            assert tracked_kwargs.get("input_data") == "test input"

    @pytest.mark.asyncio
    async def test_run_with_cwd(self):
        """Run should pass cwd to run_command."""
        tracked_kwargs = {}
        async def tracking_run_command(cmd, **kwargs):
            tracked_kwargs.update(kwargs)
            return CommandResult(returncode=0, stdout="", stderr="", command="")

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = MockToolWrapper("/path/to/mocktool")
            wrapper._available = True
            await wrapper.run(["--help"], cwd=Path("/tmp"))
            assert tracked_kwargs.get("cwd") == Path("/tmp")


class TestPureDNSWrapper:
    """Tests for PureDNSWrapper."""

    def test_get_version_args(self):
        """PureDNS should use '-version' flag."""
        wrapper = PureDNSWrapper("/usr/bin/puredns")
        assert wrapper.get_version_args() == ["-version"]

    def test_name(self):
        """PureDNS name should be 'puredns'."""
        wrapper = PureDNSWrapper("/usr/bin/puredns")
        assert wrapper.name == "puredns"

    @pytest.mark.asyncio
    async def test_resolve_calls_run(self):
        """Resolve should call run with correct args."""
        tracked_calls = []
        async def tracking_run_command(cmd, **kwargs):
            tracked_calls.append(cmd)
            return CommandResult(returncode=0, stdout="", stderr="", command="")

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = PureDNSWrapper("/usr/bin/puredns")
            wrapper._available = True
            await wrapper.resolve(
                Path("/tmp/subs.txt"),
                Path("/tmp/resolvers.txt"),
                output=Path("/tmp/resolved.txt"),
            )
            cmd = tracked_calls[0]
            assert cmd[0] == "/usr/bin/puredns"
            assert "resolve" in cmd
            assert any("subs.txt" in c for c in cmd)
            assert "-r" in cmd
            assert any("resolvers.txt" in c for c in cmd)
            assert "-w" in cmd
            assert any("resolved.txt" in c for c in cmd)

    @pytest.mark.asyncio
    async def test_resolve_without_optional_args(self):
        """Resolve without optional args should not include them."""
        tracked_calls = []
        async def tracking_run_command(cmd, **kwargs):
            tracked_calls.append(cmd)
            return CommandResult(returncode=0, stdout="", stderr="", command="")

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = PureDNSWrapper("/usr/bin/puredns")
            wrapper._available = True
            await wrapper.resolve(
                Path("/tmp/subs.txt"),
                Path("/tmp/resolvers.txt"),
            )
            cmd = tracked_calls[0]
            assert "-w" not in cmd
            assert "--wildcard" not in cmd


class TestTEWWrapper:
    """Tests for TEWWrapper."""

    def test_imports_correctly(self):
        """TEWWrapper should import without errors (regression test for List import bug)."""
        assert TEWWrapper is not None

    def test_get_version_args(self):
        """TEW should use '-version' flag."""
        wrapper = TEWWrapper("/usr/bin/tew")
        assert wrapper.get_version_args() == ["-version"]

    def test_name(self):
        """TEW name should be 'tew'."""
        wrapper = TEWWrapper("/usr/bin/tew")
        assert wrapper.name == "tew"

    @pytest.mark.asyncio
    async def test_extract_calls_run(self):
        """Extract should call run with correct args."""
        tracked_calls = []
        async def tracking_run_command(cmd, **kwargs):
            tracked_calls.append(cmd)
            return CommandResult(returncode=0, stdout="", stderr="", command="")

        with patch("sling.tools.base.run_command", new=tracking_run_command):
            wrapper = TEWWrapper("/usr/bin/tew")
            wrapper._available = True
            await wrapper.extract(
                Path("/tmp/ports.txt"),
                Path("/tmp/dns.json"),
                output=Path("/tmp/hostport.txt"),
                vhost=True,
            )
            cmd = tracked_calls[0]
            assert cmd[0] == "/usr/bin/tew"
            assert "-l" in cmd
            assert any("ports.txt" in c for c in cmd)
            assert "-dnsx" in cmd
            assert any("dns.json" in c for c in cmd)
            assert "--vhost" in cmd
            assert "-o" in cmd
            assert any("hostport.txt" in c for c in cmd)


class TestOtherToolImports:
    """Regression tests for other tool wrapper imports."""

    def test_subfinder_imports(self):
        """SubfinderWrapper should import correctly."""
        assert SubfinderWrapper is not None

    def test_subfinder_get_version_args(self):
        """Subfinder should use '-version' flag."""
        wrapper = SubfinderWrapper("/usr/bin/subfinder")
        assert wrapper.get_version_args() == ["-version"]

    def test_httpx_imports(self):
        """HTTPXWrapper should import correctly."""
        assert HTTPXWrapper is not None

    def test_httpx_get_version_args(self):
        """HTTPX should use '-version' flag."""
        wrapper = HTTPXWrapper("/usr/bin/httpx")
        assert wrapper.get_version_args() == ["-version"]

    def test_naabu_imports(self):
        """NaabuWrapper should import correctly."""
        assert NaabuWrapper is not None

    def test_naabu_get_version_args(self):
        """Naabu should use '-version' flag."""
        wrapper = NaabuWrapper("/usr/bin/naabu")
        assert wrapper.get_version_args() == ["-version"]

    def test_katana_imports(self):
        """KatanaWrapper should import correctly."""
        assert KatanaWrapper is not None

    def test_katana_get_version_args(self):
        """Katana should use '-version' flag."""
        wrapper = KatanaWrapper("/usr/bin/katana")
        assert wrapper.get_version_args() == ["-version"]
