![sling](https://github.com/haqqibrahim/Sling-Shot-R3con/assets/68786496/d32453c2-91fa-4236-8b13-f1adeacd9842)

```markdown
# Sling Shot R3con: Automate Your Bug Bounty and Pentest Reconnaissance 🎯

Sling Shot R3con is a powerful open-source reconnaissance tool designed to automate and streamline the initial phase of bug bounty and penetration testing engagements. Discover subdomains, perform DNS enumeration, conduct port scanning, identify HTTP servers, and more—all with a single command.

🔥 **Features**:
- Subdomain Discovery
- DNS Enumeration and Resolution
- Comprehensive Port Scanning
- HTTP Server Discovery
- Crawling and Scraping
- Customizable and Extensible
```

## Getting Started

### Prerequisites

- **Go Language**: A working Go environment (with `$GOPATH/bin` on your `PATH`).

### Installation

First, make the installer executable, then run it:

```bash
chmod +x ./requirements.sh
./requirements.sh
```

> **Note:** `requirements.sh` installs the following 7 Go-based tools via `go install`:
> `subfinder`, `shuffledns`, `puredns`, `dnsx`, `tew`, `katana`, and `httpx`.
>
> At the end, `requirements.sh` also runs `chmod +x ./shoot.sh` to make the main
> orchestration script executable, so you do not need to do that manually.

### Usage

Run Sling Shot R3con by providing the target domain as follows:

```bash
./shoot.sh domain.com
```

### Example

```bash
./shoot.sh google.com
```

## Workflow — Pipeline Phases in `shoot.sh`

The `shoot.sh` script defines exactly **four functions** that execute sequentially:

### 1. `setup_scan()`

Creates the scan workspace and scope files.

- Displays the ASCII-art banner.
- Creates `scope/<id>/roots.txt` with the target domain.
- Creates a unique timestamped directory under `scans/<id>-<timestamp>/`.
- Copies `roots.txt` into the scan directory.

### 2. `perform_dns_scan()`

Performs DNS enumeration and resolution.

- **Passive discovery** — pipes `roots.txt` through `subfinder`, deduplicates into `subs.txt` with `anew`.
- **Active brute-force** — runs `shuffledns` with `lists/subdomains-top1million-20000.txt` and `lists/resolvers.txt`, appends unique results to `subs.txt`.
- **Resolution** — `puredns` resolves `subs.txt` against `lists/resolvers.txt`, writing `resolved.txt`.
- **IP extraction** — `dnsx` produces `dns.json` and extracts A-record IPs into `ips.txt`.

### 3. `perform_port_scan()`

Performs port scanning and HTTP server discovery.

- Scans `ips.txt` across all 65 535 TCP ports using `naabu`, producing `ports.txt`.
- Correlates ports to hostnames via `tew` (consuming `dns.json`), producing `hostport.txt`.
- Probes for HTTP/HTTPS services with `httpx`, producing `http.json`.
- Normalises URLs (strips default `:80`/`:443` suffixes) into `http.txt`.

### 4. `perform_crawling()`

Performs crawling and JavaScript scraping.

- Spiders all URLs in `http.txt` with `katana`, writing discovered links to `crawl.txt`.
- Filters `.js` URLs from the crawl output and downloads them via `httpx -sr -srd js`.

After all four phases complete, `shoot.sh` calculates and prints the total scan duration.

## Dependencies

All dependencies are installed by `requirements.sh`. The script installs exactly these 7 tools:

| Tool | Source | Role |
|------|--------|------|
| **subfinder** | `projectdiscovery/subfinder` | Passive subdomain discovery |
| **shuffledns** | `projectdiscovery/shuffledns` | Active DNS brute-forcing |
| **puredns** | `d3mondev/puredns` | DNS resolution and wildcard filtering |
| **dnsx** | `projectdiscovery/dnsx` | DNS querying and JSON data extraction |
| **tew** | `pry0cc/tew` | Port-to-hostname correlation |
| **katana** | `projectdiscovery/katana` | Web crawling and spidering |
| **httpx** | `projectdiscovery/httpx` | HTTP probing and service discovery |

## License

Sling Shot R3con is open-source software released under the MIT License.

## Acknowledgments

Special thanks to the security community for their contributions and feedback.
