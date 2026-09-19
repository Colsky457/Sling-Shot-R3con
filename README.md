![sling](https://github.com/haqqibrahim/Sling-Shot-R3con/assets/68786496/d32453c2-91fa-4236-8b13-f1adeacd9842)

# Sling Shot R3con

Sling Shot R3con is an open-source reconnaissance CLI for bug bounty and penetration testing. It coordinates subdomain discovery, DNS enumeration, port scanning, HTTP probing, and crawling through a resumable Python pipeline.

## Features

- Subdomain Discovery
- DNS Enumeration and Resolution
- Comprehensive Port Scanning
- HTTP Server Discovery
- Crawling and Scraping
- Customizable and Extensible

## Installation

Install the Python package and all external Go-based tools:

```bash
./requirements.sh
```

For a Python-only installation, install the package and development dependencies without the external tools:

```bash
pip install -e ".[dev]"
```

The Python CLI is available as `sling` after installation. The external tools installed by `requirements.sh` are required for a complete scan.

## Commands

Start a scan:

```bash
sling scan <domain>
```

Resume the latest incomplete scan for a domain:

```bash
sling scan <domain> --resume
```

Preview the scan without executing it:

```bash
sling scan <domain> --dry-run
```

List recorded scans:

```bash
sling list
```

Show a scan's status and step progress:

```bash
sling status <scan-id>
```

List artifacts produced by a scan:

```bash
sling artifacts <scan-id>
```

`./shoot.sh domain.com` remains available as a legacy alias and wraps the Python CLI:

```bash
./shoot.sh domain.com
```

See [USAGE.md](USAGE.md) for detailed usage, configuration, pipeline steps, and output structure.

## License

Sling Shot R3con is open-source software released under the MIT License.

## Acknowledgments

Special thanks to the security community for their contributions and feedback.
