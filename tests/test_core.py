"""Tests for Sling core modules."""

import pytest
from pathlib import Path
import tempfile

from sling.config import Config, GeneralConfig, ToolPathsConfig
from sling.utils.validation import (
    validate_domain,
    validate_ip,
    validate_cidr,
    validate_target,
    sanitize_filename,
    sanitize_path,
)
from sling.utils.subprocess import resolve_ports, get_top_ports, parse_port_range
from sling.state import StateManager, ScanStatus, StepStatus


class TestValidation:
    """Tests for validation utilities."""

    def test_validate_domain_valid(self):
        assert validate_domain("example.com") is True
        assert validate_domain("sub.example.com") is True
        assert validate_domain("a-b.example.com") is True
        assert validate_domain("xn--example.com") is True

    def test_validate_domain_invalid(self):
        assert validate_domain("") is False
        assert validate_domain("invalid") is False
        assert validate_domain(".com") is False
        assert validate_domain("example.") is False
        assert validate_domain("example..com") is False
        assert validate_domain("-example.com") is False
        assert validate_domain("example-.com") is False

    def test_validate_ip_valid(self):
        assert validate_ip("192.168.1.1") is True
        assert validate_ip("10.0.0.1") is True
        assert validate_ip("172.16.0.1") is True
        assert validate_ip("255.255.255.255") is True

    def test_validate_ip_invalid(self):
        assert validate_ip("256.1.1.1") is False
        assert validate_ip("192.168.1") is False
        assert validate_ip("192.168.1.1.1") is False
        assert validate_ip("example.com") is False

    def test_validate_cidr_valid(self):
        assert validate_cidr("192.168.1.0/24") is True
        assert validate_cidr("10.0.0.0/8") is True
        assert validate_cidr("172.16.0.0/12") is True

    def test_validate_cidr_invalid(self):
        assert validate_cidr("192.168.1.0/33") is False
        assert validate_cidr("192.168.1/24") is False
        assert validate_cidr("example.com/24") is False

    def test_validate_target(self):
        assert validate_target("example.com") is True
        assert validate_target("192.168.1.1") is True
        assert validate_target("192.168.1.0/24") is True
        assert validate_target("invalid") is False

    def test_sanitize_filename(self):
        assert sanitize_filename("test/file.txt") == "test_file.txt"
        assert sanitize_filename('test:file') == "test_file"
        assert sanitize_filename('test<file>') == "test_file_"
        assert len(sanitize_filename("a" * 300)) == 255

    def test_sanitize_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            good = base / "subdir" / "file.txt"
            assert sanitize_path(good, base) == good.resolve()
            
            # This should raise
            with pytest.raises(ValueError):
                sanitize_path(Path("/etc/passwd"), base)


class TestPortResolution:
    """Tests for port resolution utilities."""

    def test_parse_port_range(self):
        assert parse_port_range("80,443") == [80, 443]
        assert parse_port_range("1-10") == list(range(1, 11))
        assert parse_port_range("80,100-200,443") == [80] + list(range(100, 201)) + [443]

    def test_get_top_ports(self):
        ports = get_top_ports(10)
        assert len(ports) == 10
        assert ports[0] == 80
        assert ports[1] == 443

    def test_resolve_ports_full(self):
        ports = resolve_ports("full")
        assert len(ports) == 65535
        assert ports[0] == 1
        assert ports[-1] == 65535

    def test_resolve_ports_top(self):
        ports = resolve_ports("top-100")
        assert len(ports) == 100
        assert ports[0] == 80

    def test_get_top_ports_500_unique(self):
        """Regression: duplicate 50851 used to make top-500 return 496 unique ports."""
        ports = get_top_ports(500)
        assert len(ports) == 500
        assert len(set(ports)) == 500
        assert ports[0] == 80

    def test_resolve_ports_custom(self):
        ports = resolve_ports("80,443,8080")
        assert ports == [80, 443, 8080]


class TestConfig:
    """Tests for configuration."""

    def test_default_config(self):
        config = Config()
        assert config.general.log_level == "INFO"
        assert config.general.max_parallel == 4
        assert config.tools.subfinder == "subfinder"
        assert config.dns.passive.enabled is True
        assert config.port.scan.ports == "top-1000"

    def test_config_from_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
general:
  log_level: "DEBUG"
  max_parallel: 8
dns:
  passive:
    enabled: false
""")
            f.flush()
            config = Config(_yaml_file=f.name)
            assert config.general.log_level == "DEBUG"
            assert config.general.max_parallel == 8
            assert config.dns.passive.enabled is False


class TestStateManager:
    """Tests for state management."""

    def test_create_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.general.output_dir = Path(tmpdir)
            state = StateManager(config)
            
            scan_id = state.create_scan("example.com")
            assert len(scan_id) == 8
            
            scan = state.get_scan(scan_id)
            assert scan is not None
            assert scan["domain"] == "example.com"
            assert scan["status"] == ScanStatus.PENDING.value

    def test_update_scan_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.general.output_dir = Path(tmpdir)
            state = StateManager(config)
            
            scan_id = state.create_scan("example.com")
            state.update_scan_status(scan_id, ScanStatus.RUNNING, "dns")
            
            scan = state.get_scan(scan_id)
            assert scan["status"] == ScanStatus.RUNNING.value
            assert scan["current_step"] == "dns"

    def test_step_management(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.general.output_dir = Path(tmpdir)
            state = StateManager(config)
            
            scan_id = state.create_scan("example.com")
            state.create_step(scan_id, "dns")
            
            state.update_step_status(scan_id, "dns", StepStatus.RUNNING)
            step = state.get_step(scan_id, "dns")
            assert step["status"] == StepStatus.RUNNING.value
            
            state.update_step_status(scan_id, "dns", StepStatus.COMPLETED, "/path/to/output")
            step = state.get_step(scan_id, "dns")
            assert step["status"] == StepStatus.COMPLETED.value
            assert step["output_path"] == "/path/to/output"

    def test_can_resume_step(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.general.output_dir = Path(tmpdir)
            state = StateManager(config)
            
            scan_id = state.create_scan("example.com")
            state.create_step(scan_id, "dns")
            state.update_step_status(scan_id, "dns", StepStatus.COMPLETED)
            
            assert state.can_resume_step(scan_id, "dns") is True
            assert state.can_resume_step(scan_id, "port") is False

    def test_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.general.output_dir = Path(tmpdir)
            state = StateManager(config)
            
            scan_id = state.create_scan("example.com")
            state.add_artifact(scan_id, "dns", "subdomains", "/path/to/subs.txt", 100)
            
            artifacts = state.get_artifacts(scan_id)
            assert len(artifacts) == 1
            assert artifacts[0]["type"] == "subdomains"
            assert artifacts[0]["count"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])