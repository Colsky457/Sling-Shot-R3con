# Sling - Usage Guide

## Installation

```bash
# Install dependencies
pip install -e ".[dev]"

# Install external Go tools (required)
./requirements.sh
```

## Quick Start

```bash
# Scan a domain
sling scan example.com

# Resume interrupted scan
sling scan example.com --resume

# Dry run to see what would execute
sling scan example.com --dry-run

# List all scans
sling list

# Show scan status
sling status <scan-id>

# List scan artifacts
sling artifacts <scan-id>
```

## Commands

### `sling scan <domain>`

Start a new reconnaissance scan for the given domain.

Options:
- `-r, --resume` - Resume an interrupted scan for this domain
- `--dry-run` - Show execution plan without running

### `sling resume <scan-id>`

Resume a specific scan by ID.

### `sling list`

List all scans with their status.

### `sling status <scan-id>`

Show detailed status of a scan including step progress and artifacts.

### `sling artifacts <scan-id>`

List all artifacts produced by a scan.

## Configuration

Sling uses a `config.yaml` file for configuration. All settings can be overridden via environment variables with the `SLING_` prefix (e.g., `SLING_GENERAL__LOG_LEVEL=DEBUG`).

### Key Configuration Sections

- **general** - Output directories, logging, parallelism
- **tools** - Paths to external tools (auto-detected if in PATH)
- **wordlists** - Paths to resolver and subdomain wordlists
- **dns** - DNS enumeration settings (passive, active, resolution)
- **port** - Port scanning and HTTP probing settings
- **crawl** - Web crawling settings

### Example Config

```yaml
general:
  output_dir: "./scans"
  log_level: "INFO"
  max_parallel: 4

dns:
  passive:
    enabled: true
    timeout: 300
  active:
    enabled: true
    timeout: 600
  resolution:
    enabled: true
    timeout: 300

port:
  scan:
    enabled: true
    ports: "top-1000"
    rate: 1000
  http_probe:
    enabled: true
    timeout: 30

crawl:
  enabled: true
  depth: 2
  timeout: 600
  js_extraction: true
```

## Pipeline Steps

1. **DNS Enumeration** (`dns`)
   - Passive: subfinder
   - Active: shuffledns with wordlist
   - Resolution: puredns
   - Records: dnsx (A, AAAA, CNAME, NS, MX, TXT)

2. **Port Scanning** (`port`)
   - Scan: naabu (configurable port range)
   - Extract host:port: tew
   - HTTP probe: httpx

3. **Crawling** (`crawl`)
   - Crawl: katana
   - JS extraction: httpx download

## Output Structure

```
scans/
└── example.com-abc12345/
    ├── roots.txt          # Input domain
    ├── subs.txt           # All discovered subdomains
    ├── resolved.txt       # Resolved subdomains
    ├── dns.json           # DNS records (JSON)
    ├── ips.txt            # Extracted IP addresses
    ├── ports.txt          # Open ports
    ├── hostport.txt       # Host:port pairs
    ├── http.json          # HTTP services (JSON)
    ├── http.txt           # HTTP URLs
    ├── crawl.txt          # Crawled URLs
    ├── js_urls.txt        # JavaScript file URLs
    └── state.db           # SQLite state database
```

## State Management

Sling uses SQLite for persistent state tracking:
- Scan metadata (status, timestamps)
- Step progress (pending/running/completed/failed)
- Artifacts produced by each step
- Resume capability from last successful step

## Architecture

```
sling/
├── cli.py              # Click CLI commands
├── config.py           # Pydantic configuration models
├── logging.py          # Structured logging (structlog + Rich)
├── state.py            # SQLite state management
├── pipeline/
│   ├── base.py         # Pipeline orchestration (DAG-based)
│   ├── dns.py          # DNS enumeration step
│   ├── port.py         # Port scanning step
│   └── crawl.py        # Crawling step
├── tools/
│   ├── base.py         # Tool wrapper base classes
│   ├── subfinder.py    # Subfinder wrapper
│   ├── shuffledns.py   # ShuffleDNS wrapper
│   ├── puredns.py      # PureDNS wrapper
│   ├── dnsx.py         # DNSX wrapper
│   ├── naabu.py        # Naabu wrapper
│   ├── tew.py          # TEW wrapper
│   ├── httpx.py        # HTTPX wrapper
│   └── katana.py       # Katana wrapper
└── utils/
    ├── subprocess.py   # Safe async subprocess execution
    ├── validation.py   # Input validation & sanitization
    └── network.py      # Rate limiting & connection pooling
```

## Key Features

- **Modular Design**: Each pipeline step is independent and reusable
- **Resume Capability**: Interrupted scans can resume from last completed step
- **Structured Logging**: JSON logs for parsing, human-readable for terminal
- **Configuration-Driven**: All behavior configurable via YAML/env vars
- **Async Execution**: Parallel step execution where dependencies allow
- **Error Handling**: Retries with exponential backoff, timeouts
- **State Persistence**: SQLite database tracks all scan progress
- **Type Safety**: Full type hints with mypy strict mode

## Development

```bash
# Run tests
pytest tests/

# Lint
ruff check .

# Type check
mypy sling/
```

## Migration from shoot.sh

The original `shoot.sh` bash script is preserved. The new Python version provides:
- Equivalent functionality with better reliability
- Resume capability (was not possible before)
- Structured outputs and state tracking
- Configurable pipeline steps
- Better error handling and observability

Run both in parallel during transition:
```bash
# Old way
./shoot.sh example.com

# New way
sling scan example.com
```