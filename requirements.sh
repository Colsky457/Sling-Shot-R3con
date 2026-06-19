#!/bin/bash

set -euo pipefail

# Pin dependency versions to prevent supply-chain attacks.
# Review and update these versions periodically.
SUBFINDER_VERSION="v2.6.6"
SHUFFLEDNS_VERSION="v1.1.0"
PUREDNS_VERSION="v2.1.1"
DNSX_VERSION="v1.2.1"
TEW_VERSION="v0.3.1"
KATANA_VERSION="v1.1.0"
HTTPX_VERSION="v1.6.8"
NAABU_VERSION="v2.3.1"

echo "[*] Installing pinned dependency versions..."

go install -v "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@${SUBFINDER_VERSION}"
go install -v "github.com/projectdiscovery/shuffledns/cmd/shuffledns@${SHUFFLEDNS_VERSION}"
go install "github.com/d3mondev/puredns/v2@${PUREDNS_VERSION}"
go install -v "github.com/projectdiscovery/dnsx/cmd/dnsx@${DNSX_VERSION}"
go install "github.com/pry0cc/tew@${TEW_VERSION}"
go install "github.com/projectdiscovery/katana/cmd/katana@${KATANA_VERSION}"
go install -v "github.com/projectdiscovery/httpx/cmd/httpx@${HTTPX_VERSION}"
go install -v "github.com/projectdiscovery/naabu/v2/cmd/naabu@${NAABU_VERSION}"

chmod +x ./shoot.sh

echo "[*] All dependencies installed successfully."
