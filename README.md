![sling](https://github.com/haqqibrahim/Sling-Shot-R3con/assets/68786496/d32453c2-91fa-4236-8b13-f1adeacd9842)

# Sling Shot R3con: Automate Your Bug Bounty and Pentest Reconnaissance 🎯

Sling Shot R3con is a powerful open-source reconnaissance tool designed to automate and streamline the initial phase of bug bounty and penetration testing engagements. Discover subdomains, perform DNS enumeration, conduct port scanning, identify HTTP servers, and more—all with a single command.

🔥 **Features**:
- Subdomain Discovery
- DNS Enumeration and Resolution
- Comprehensive Port Scanning
- HTTP Server Discovery
- Crawling and Scraping
- Customizable and Extensible
- Resume Interrupted Scans
- Structured State Management (SQLite)

## Installation

### Full Installation (Recommended)

Install both Go tools and Python dependencies:

```bash
chmod +x ./requirements.sh
./requirements.sh
```

This installs:
- Go tools: subfinder, shuffledns, puredns, dnsx, tew, katana, httpx, naabu
- Python package: sling with dev dependencies (click, pydantic, structlog, rich, etc.)

### Python-Only Installation

If you already have the Go tools installed:

```bash
pip install -e ".[dev]"
```

## Usage

### Python CLI (New)

The `sling` command provides a full-featured CLI:

```bash
# Scan a domain
sling scan example.com

# Resume interrupted scan for a domain
sling scan example.com --resume

# Dry run to see execution plan without running
sling scan example.com --dry-run

# List all scans
sling list

# Show detailed scan status
sling status <scan-id>

# List scan artifacts
sling artifacts <scan-id>

# Resume a specific scan by ID
sling resume <scan-id>
```

### Legacy Wrapper (Backward Compatible)

The original `./shoot.sh` still works as a wrapper around the Python CLI:

```bash
./shoot.sh example.com
./shoot.sh example.com --resume
./shoot.sh example.com --dry-run
```

This preserves the familiar ASCII banner and forwards all arguments to `python3 -m sling.cli scan`.

## Configuration

Sling uses a `config.yaml` file for configuration. All settings can be overridden via environment variables with the `SLING_` prefix (e.g., `SLING_GENERAL__LOG_LEVEL=DEBUG`).

### Key Configuration Sections

| Section | Description |
|---------|-------------|
| `general` | Output directories, logging, parallelism |
| `tools` | Paths to external tools (auto-detected if in PATH) |
| `wordlists` | Paths to resolver and subdomain wordlists |
| `dns` | DNS enumeration settings (passive, active, resolution) |
| `port` | Port scanning and HTTP probing settings |
| `crawl` | Web crawling settings |

### Example Config

```yaml
general:
  output_dir: "./scans"
  temp_dir: "./tmp"
  log_level: "INFO"
  max_parallel: 4

tools:
  subfinder: "subfinder"
  shuffledns: "shuffledns"
  puredns: "puredns"
  dnsx: "dnsx"
  naabu: "naabu"
  tew: "tew"
  httpx: "httpx"
  katana: "katana"

wordlists:
  resolvers: "lists/resolvers.txt"
  subdomains: "lists/subdomains-top1million-20000.txt"
  auto_update: true

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
    timeout: 600
  http_probe:
    enabled: true
    timeout: 30

crawl:
  enabled: true
  depth: 2
  timeout: 600
  js_extraction: true
```

See `config.yaml` for the full default configuration.

## Commands Reference

| Command | Description |
|---------|-------------|
| `sling scan <domain>` | Start a new reconnaissance scan |
| `sling scan <domain> --resume` | Resume interrupted scan for domain |
| `sling scan <domain> --dry-run` | Show execution plan without running |
| `sling resume <scan-id>` | Resume a specific scan by ID |
| `sling list` | List all scans with their status |
| `sling status <scan-id>` | Show detailed status of a scan |
| `sling artifacts <scan-id>` | List all artifacts produced by a scan |

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

## License

Sling Shot R3con is open-source software released under the MIT License.

## Acknowledgments

Special thanks to the security community for their contributions and feedback.

See `USAGE.md` for detailed usage, architecture, and development guide.
