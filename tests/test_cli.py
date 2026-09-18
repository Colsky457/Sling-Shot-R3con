"""Tests for CLI commands."""

from click.testing import CliRunner
from unittest.mock import MagicMock, patch

import pytest

from sling.cli import cli, scan, list as list_cmd, status, artifacts
from sling.state import StateManager, ScanStatus, StepStatus


def make_mock_state(scans=None, steps=None, artifacts=None, scan_detail=None):
    """Create a mock StateManager with configurable return values."""
    state = MagicMock(spec=StateManager)
    if scans is not None:
        state.list_scans.return_value = scans
    else:
        state.list_scans.return_value = []
    if steps is not None:
        state.get_steps.return_value = steps
    if artifacts is not None:
        state.get_artifacts.return_value = artifacts
    if scan_detail is not None:
        state.get_scan.return_value = scan_detail
    else:
        state.get_scan.return_value = None
    state.can_resume_step.return_value = False
    return state


class TestScanDryRun:
    """Tests for `sling scan --dry-run`."""

    @pytest.mark.asyncio
    async def test_dry_run_shows_steps(self):
        """Dry run should display steps without executing."""
        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "example.com", "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output or "dry" in result.output.lower()

    @pytest.mark.asyncio
    async def test_dry_run_invalid_domain_fails(self):
        """Dry run with invalid domain should fail."""
        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "invalid_domain!", "--dry-run"])
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_dry_run_creates_scan(self):
        """Dry run should create a scan record."""
        mock_state = make_mock_state()
        with patch("sling.cli.setup_logging"):
            with patch("sling.cli.StateManager", return_value=mock_state):
                with patch("sling.cli.Config") as MockConfig:
                    mock_config = MagicMock()
                    mock_config.general.output_dir = MagicMock()
                    mock_config.general.log_level = "INFO"
                    with patch("sling.cli.DNSStep"), patch("sling.cli.PortStep"), patch("sling.cli.CrawlStep"), patch("sling.cli.PipelineOrchestrator"):
                        runner = CliRunner()
                        result = runner.invoke(
                            cli, ["scan", "example.com", "--dry-run"]
                        )
                        assert mock_state.create_scan.called


class TestListCommand:
    """Tests for `sling list`."""

    def test_list_shows_scans(self):
        """List should display scans in a table."""
        mock_state = make_mock_state(
            scans=[
                {
                    "id": "abc12345",
                    "domain": "example.com",
                    "status": "completed",
                    "created_at": "2024-01-01T00:00:00",
                    "current_step": None,
                },
                {
                    "id": "def67890",
                    "domain": "test.com",
                    "status": "running",
                    "created_at": "2024-01-02T00:00:00",
                    "current_step": "dns",
                },
            ]
        )
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0
            assert "example.com" in result.output
            assert "test.com" in result.output
            assert "abc12345" in result.output
            assert "def67890" in result.output

    def test_list_empty(self):
        """List with no scans should still succeed."""
        mock_state = make_mock_state(scans=[])
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0

    def test_list_calls_list_scans(self):
        """List should call state.list_scans()."""
        mock_state = make_mock_state()
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            runner.invoke(cli, ["list"])
            mock_state.list_scans.assert_called_once()


class TestStatusCommand:
    """Tests for `sling status`."""

    def test_status_shows_scan_details(self):
        """Status should display scan details."""
        mock_state = make_mock_state(
            scan_detail={
                "id": "abc12345",
                "domain": "example.com",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T01:00:00",
                "current_step": "port",
            }
        )
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            result = runner.invoke(cli, ["status", "abc12345"])
            assert result.exit_code == 0
            assert "abc12345" in result.output
            assert "example.com" in result.output

    def test_status_not_found(self):
        """Status for non-existent scan should fail."""
        mock_state = make_mock_state(scan_detail=None)
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            result = runner.invoke(cli, ["status", "nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_status_calls_get_scan(self):
        """Status should call state.get_scan()."""
        mock_state = make_mock_state(
            scan_detail={
                "id": "abc12345",
                "domain": "example.com",
                "status": "pending",
                "created_at": "",
                "updated_at": "",
                "current_step": None,
            }
        )
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            runner.invoke(cli, ["status", "abc12345"])
            mock_state.get_scan.assert_called_once_with("abc12345")


class TestArtifactsCommand:
    """Tests for `sling artifacts`."""

    def test_artifacts_shows_artifact_list(self):
        """Artifacts should display artifact list."""
        mock_state = make_mock_state(
            scan_detail={
                "id": "abc12345",
                "domain": "example.com",
                "status": "completed",
                "created_at": "",
                "updated_at": "",
                "current_step": None,
            },
            artifacts=[
                {
                    "step_name": "dns",
                    "type": "subdomains",
                    "count": 100,
                    "path": "/tmp/scans/subs.txt",
                },
                {
                    "step_name": "port",
                    "type": "ports",
                    "count": 50,
                    "path": "/tmp/scans/ports.txt",
                },
            ],
        )
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            result = runner.invoke(cli, ["artifacts", "abc12345"])
            assert result.exit_code == 0
            assert "subdomains" in result.output
            assert "100" in result.output
            assert "ports" in result.output
            assert "50" in result.output

    def test_artifacts_no_artifacts(self):
        """Artifacts with no artifacts should show message."""
        mock_state = make_mock_state(
            scan_detail={
                "id": "abc12345",
                "domain": "example.com",
                "status": "completed",
                "created_at": "",
                "updated_at": "",
                "current_step": None,
            },
            artifacts=[],
        )
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            result = runner.invoke(cli, ["artifacts", "abc12345"])
            assert result.exit_code == 0
            assert "No artifacts" in result.output or "no artifacts" in result.output.lower()

    def test_artifacts_not_found(self):
        """Artifacts for non-existent scan should fail."""
        mock_state = make_mock_state(scan_detail=None)
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            result = runner.invoke(cli, ["artifacts", "nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_artifacts_calls_get_scan_and_get_artifacts(self):
        """Artifacts should call state methods."""
        mock_state = make_mock_state(
            scan_detail={
                "id": "abc12345",
                "domain": "example.com",
                "status": "completed",
                "created_at": "",
                "updated_at": "",
                "current_step": None,
            },
            artifacts=[],
        )
        with patch("sling.cli.StateManager", return_value=mock_state):
            runner = CliRunner()
            runner.invoke(cli, ["artifacts", "abc12345"])
            mock_state.get_scan.assert_called_once_with("abc12345")
            mock_state.get_artifacts.assert_called_once_with("abc12345")


class TestCLIImport:
    """Regression tests for CLI imports."""

    def test_cli_group_exists(self):
        """CLI group should exist."""
        assert cli is not None

    def test_scan_command_exists(self):
        """Scan command should exist."""
        assert scan is not None

    def test_list_command_exists(self):
        """List command should exist."""
        assert list_cmd is not None

    def test_status_command_exists(self):
        """Status command should exist."""
        assert status is not None

    def test_artifacts_command_exists(self):
        """Artifacts command should exist."""
        assert artifacts is not None
