"""Input validation and sanitization utilities."""

import re
from pathlib import Path
from typing import List


DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

IP_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

CIDR_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(?:[0-9]|[12][0-9]|3[0-2])$"
)


def validate_domain(domain: str) -> bool:
    """Validate a domain name."""
    if not domain or len(domain) > 253:
        return False
    return bool(DOMAIN_REGEX.match(domain))


def validate_ip(ip: str) -> bool:
    """Validate an IPv4 address."""
    return bool(IP_REGEX.match(ip))


def validate_cidr(cidr: str) -> bool:
    """Validate a CIDR notation."""
    return bool(CIDR_REGEX.match(cidr))


def validate_target(target: str) -> bool:
    """Validate a target (domain, IP, or CIDR)."""
    return validate_domain(target) or validate_ip(target) or validate_cidr(target)


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove path separators and other dangerous characters
    name = name.replace("/", "_").replace("\\", "_")
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name)
    # Limit length
    return name[:255]


def sanitize_path(path: Path, base: Path) -> Path:
    """Ensure a path is within the base directory (prevent path traversal)."""
    try:
        resolved = path.resolve()
        base_resolved = base.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise ValueError(f"Path {path} escapes base directory {base}")
        return resolved
    except (ValueError, RuntimeError):
        raise ValueError(f"Invalid path: {path}")


def validate_wordlist(path: Path) -> bool:
    """Validate a wordlist file exists and is readable."""
    if not path.exists():
        return False
    if not path.is_file():
        return False
    # Check file is not empty
    try:
        return path.stat().st_size > 0
    except OSError:
        return False


def read_lines(path: Path, max_lines: int = 1000000) -> List[str]:
    """Safely read lines from a file with limit."""
    lines = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                line = line.strip()
                if line and not line.startswith("#"):
                    lines.append(line)
    except OSError:
        pass
    return lines