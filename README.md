![sling](https://github.com/haqqibrahim/Sling-Shot-R3con/assets/68786496/d32453c2-91fa-4236-8b13-f1adeacd9842)

# Sling Shot R3con: Automate Your Bug Bounty and Pentest Reconnaissance

Sling Shot R3con is a powerful open-source reconnaissance tool designed to automate and streamline the initial phase of bug bounty and penetration testing engagements. Discover subdomains, perform DNS enumeration, conduct port scanning, identify HTTP servers, and more—all with a single command.

**Features**:
- Subdomain Discovery
- DNS Enumeration and Resolution
- Comprehensive Port Scanning
- HTTP Server Discovery
- Crawling and Scraping
- Customizable and Extensible

## Getting Started

### Prerequisites

- [Go](https://go.dev/dl/) (required to install tool dependencies)
- [jq](https://jqlang.github.io/jq/download/) (installed automatically by the setup script on supported systems)

Install the required dependencies by running:

```bash
chmod +x ./requirements.sh
./requirements.sh
```

### Usage

Run Sling Shot R3con by providing the target domain as follows:

```bash
./shoot.sh domain.com
```

### Example:

```bash
./shoot.sh google.com
```

## License

Sling Shot R3con is open-source software released under the [MIT License](LICENSE).

## Acknowledgments

Special thanks to the security community for their contributions and feedback.
