# Sling Shot R3con - Codebase Exploration & Reconstruction Plan

## Current Codebase Overview

### Project Structure
```
├── shoot.sh                          # Main orchestration script (bash, 128 lines)
├── requirements.sh                   # Dependency installer (bash, 11 lines)
├── lists/
│   ├── resolvers.txt                 # 99,972 DNS resolvers
│   ├── resolvers.txt.save            # Backup copy
│   └── subdomains-top1million-20000.txt  # 19,966 subdomain wordlist
└── README.md                         # Basic documentation
```

### Technology Stack
- **Language**: Bash (orchestration)
- **External Tools** (installed via Go):
  - `subfinder` - Passive subdomain enumeration
  - `shuffledns` - Active subdomain bruteforce
  - `puredns` - DNS resolution & validation
  - `dnsx` - DNS toolkit
  - `naabu` - Port scanner
  - `tew` - Host:port extraction from DNS
  - `httpx` - HTTP probing
  - `katana` - Web crawler
- **Utilities**: `jq`, `anew`, `sort`, `sed`, `cut`

### Current Pipeline Flow
```
1. setup_scan()
   - Create scan directory (scans/<domain>-<timestamp>/)
   - Create roots.txt with target domain

2. perform_dns_scan()
   - subfinder (passive) → subs.txt
   - shuffledns (active bruteforce) → subs.txt
   - puredns resolve → resolved.txt
   - dnsx → dns.json + ips.txt

3. perform_port_scan()
   - naabu (full port scan 1-65535) → ports.txt
   - tew + httpx → http.json + http.txt

4. perform_crawling()
   - katana crawl → crawl.txt
   - Extract .js files → httpx download
```

---

## Issues & Limitations

### Architecture
- **Monolithic bash script** - All logic in one file, hard to maintain
- **No modular design** - Cannot reuse individual components
- **Tight coupling** - Hardcoded paths, tools, and parameters
- **No configuration system** - All options hardcoded

### Reliability
- **No error handling** - Pipeline continues on tool failures
- **No retry logic** - Network issues cause silent failures
- **No resume capability** - Interrupted scans must restart from scratch
- **No state tracking** - Cannot determine what completed

### Observability
- **Basic logging** - Only colored echo statements
- **No structured logs** - Cannot parse/analyze programmatically
- **No progress tracking** - Long-running tools give no feedback
- **No metrics** - No timing, counts, or performance data

### Usability
- **Single output format** - Text files only
- **No filtering options** - Cannot customize scan scope
- **No dry-run mode** - Cannot preview what would run
- **Hardcoded wordlists** - Cannot easily swap/extend

### Performance
- **Sequential execution** - No parallelization where possible
- **No rate limiting** - May trigger WAFs/bans
- **Full port scan (1-65535)** - Extremely slow, rarely needed
- **No caching** - Repeated runs re-do all work

### Security
- **No input validation** - Domain argument used directly in paths
- **Shell injection risk** - Variables used in commands without quoting
- **No output sanitization** - Tool outputs written directly to files

---

## Reconstruction Plan

### Phase 1: Foundation (Language & Architecture)
**Goal**: Rewrite in a maintainable language with modular architecture

**Recommended Language: Python 3.11+** (or Go/Rust)
- Rich ecosystem for CLI tools, subprocess management, async I/O
- Excellent libraries: click/typer (CLI), pydantic (config), structlog (logging)
- Easy integration with existing Go tools via subprocess
- Type hints for maintainability

**Architecture**:
```
sling/
├── __init__.py
├── cli.py              # Click/Typer command definitions
├── config.py           # Pydantic config models + YAML/TOML loading
├── logging.py          # Structured logging setup
├── state.py            # SQLite/JSON state management
├── pipeline/
│   ├── __init__.py
│   ├── base.py         # Base step class with retry, timeout, checkpointing
│   ├── dns.py          # DNS enumeration & resolution steps
│   ├── port.py         # Port scanning & HTTP discovery steps
│   ├── crawl.py        # Crawling & JS scraping steps
│   └── orchestrator.py # Pipeline execution with DAG
├── tools/
│   ├── __init__.py
│   ├── subfinder.py    # Wrapper with args, parsing, error handling
│   ├── shuffledns.py
│   ├── puredns.py
│   ├── dnsx.py
│   ├── naabu.py
│   ├── tew.py
│   ├── httpx.py
│   └── katana.py
├── wordlists/
│   ├── __init__.py
│   ├── manager.py      # Download, update, validate wordlists
│   └── builtins.py     # Embedded default wordlists
├── output/
│   ├── __init__.py
│   ├── writers.py      # JSON, CSV, TXT, SQLite writers
│   └── formatters.py   # Normalize tool outputs
└── utils/
    ├── __init__.py
    ├── subprocess.py   # Safe subprocess with timeout, retries
    ├── validation.py   # Input validation, sanitization
    └── network.py      # Rate limiting, connection pooling
```

### Phase 2: Configuration & State Management
**Goal**: Externalize all configuration, add persistent state

**Config File (config.yaml)**:
```yaml
# Global settings
general:
  output_dir: "./scans"
  temp_dir: "./tmp"
  log_level: "INFO"
  max_parallel: 4

# Tool paths (auto-detected if not set)
tools:
  subfinder: "subfinder"
  shuffledns: "shuffledns"
  puredns: "puredns"
  dnsx: "dnsx"
  naabu: "naabu"
  tew: "tew"
  httpx: "httpx"
  katana: "katana"

# Wordlist settings
wordlists:
  resolvers: "lists/resolvers.txt"
  subdomains: "lists/subdomains-top1million-20000.txt"
  auto_update: true

# Pipeline step configs
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
    ports: "top-1000"  # or "full", "top-100", comma-separated
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

**State Database (SQLite)**:
```sql
CREATE TABLE scans (
  id TEXT PRIMARY KEY,
  domain TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  status TEXT,  -- pending, running, completed, failed, paused
  current_step TEXT
);

CREATE TABLE steps (
  scan_id TEXT,
  name TEXT,
  status TEXT,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  output_path TEXT,
  error TEXT,
  PRIMARY KEY (scan_id, name)
);

CREATE TABLE artifacts (
  scan_id TEXT,
  step_name TEXT,
  type TEXT,  -- subdomains, ips, ports, urls, etc.
  path TEXT,
  count INTEGER,
  created_at TIMESTAMP
);
```

### Phase 3: Core Pipeline Implementation
**Goal**: Implement each pipeline step with proper error handling, retries, checkpointing

**Step Interface**:
```python
class PipelineStep(ABC):
    name: str
    dependencies: List[str]  # Step names that must complete first
    
    @abstractmethod
    async def execute(self, context: ScanContext) -> StepResult:
        pass
    
    @abstractmethod
    def get_output_paths(self, context: ScanContext) -> List[Path]:
        pass
    
    def can_resume(self, context: ScanContext) -> bool:
        # Check if output files exist and are valid
        pass
```

**Key Features per Step**:
- **Timeout** per tool invocation
- **Retry** with exponential backoff (configurable)
- **Checkpoint** - save progress after each tool
- **Validation** - verify outputs before proceeding
- **Skip if complete** - resume from last successful step

### Phase 4: Enhanced Features
**Goal**: Add production-grade features

| Feature | Description |
|---------|-------------|
| **Parallel execution** | Run independent steps concurrently (DAG-based) |
| **Rate limiting** | Token bucket per tool/target |
| **Dry-run mode** | Print commands without executing |
| **Output formats** | JSON, CSV, SQLite, Markdown reports |
| **Filtering** | Include/exclude patterns for subdomains, ports, URLs |
| **Notifications** | Webhook, email, Slack on completion/failure |
| **Scheduling** | Cron-like repeat scans |
| **API mode** | REST API for integration |

### Phase 5: Testing & Quality
**Goal**: Comprehensive test coverage

- **Unit tests**: Each tool wrapper, config parsing, state management
- **Integration tests**: Full pipeline with mock tools
- **Contract tests**: Verify tool output parsing against real samples
- **Property tests**: Fuzz input validation
- **E2E tests**: Run against test domains (example.com, etc.)

### Phase 6: Documentation & Distribution
**Goal**: Production-ready distribution

- **Documentation**: MkDocs with API reference, guides, examples
- **Packaging**: PyPI package, Docker image, Homebrew, AUR
- **CI/CD**: GitHub Actions for test, build, release
- **Binaries**: PyInstaller/PyOxidizer for standalone executables

---

## Migration Strategy

### Option A: Incremental (Recommended)
1. Create new `sling/` package alongside `shoot.sh`
2. Implement config system first
3. Port one pipeline step at a time
4. Run old and new in parallel, compare outputs
5. Switch default entry point when parity achieved

### Option B: Clean Rewrite
1. Archive current codebase
2. Build new version from scratch
3. Single cutover

---

## Immediate Next Steps

1. **Create project structure** with Python packaging (pyproject.toml)
2. **Implement config system** with Pydantic + YAML
3. **Build tool wrappers** for subfinder, shuffledns, puredns, dnsx
4. **Implement DNS pipeline step** with state persistence
5. **Add CLI** with scan, resume, status, list commands
6. **Write tests** for each component
7. **Document** architecture and usage

---

## Resource Requirements

### Dependencies (Python)
```toml
[project]
dependencies = [
    "click>=8.1",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "pyyaml>=6.0",
    "structlog>=24.0",
    "rich>=13.0",        # Pretty CLI output
    "tenacity>=8.0",     # Retry logic
    "aiofiles>=23.0",    # Async file I/O
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-mock>=3.10",
    "ruff>=0.1",
    "mypy>=1.0",
    "pre-commit>=3.0",
]
```

### System Dependencies (unchanged)
- Go tools: subfinder, shuffledns, puredns, dnsx, naabu, tew, httpx, katana
- jq, anew (for compatibility during transition)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tool API changes | Medium | High | Version pinning, wrapper abstraction |
| Performance regression | Low | Medium | Benchmark each step, profile |
| Missing edge cases | Medium | Medium | Comprehensive test corpus |
| User migration friction | High | Low | Backward-compatible CLI, config migration |

---

## Success Criteria

- [ ] All current functionality preserved
- [ ] Configurable via YAML/TOML
- [ ] Resume interrupted scans
- [ ] Structured logging (JSON + human)
- [ ] Unit test coverage >80%
- [ ] Documentation for all public APIs
- [ ] Packaged for PyPI + Docker
- [ ] Performance >= current bash version