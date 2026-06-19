#!/bin/bash
set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO] $*${NC}"; }
log_error() { echo -e "${RED}[ERROR] $*${NC}" >&2; }

if ! command -v go &>/dev/null; then
    log_error "Go is not installed. Please install Go first: https://go.dev/doc/install"
    exit 1
fi

tools=(
    "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    "github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest"
    "github.com/d3mondev/puredns/v2@latest"
    "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
    "github.com/pry0cc/tew@latest"
    "github.com/projectdiscovery/katana/cmd/katana@latest"
    "github.com/projectdiscovery/httpx/cmd/httpx@latest"
)

failed=()

for tool in "${tools[@]}"; do
    log_info "Installing $tool"
    if ! go install -v "$tool"; then
        log_error "Failed to install $tool"
        failed+=("$tool")
    fi
done

if [ ${#failed[@]} -gt 0 ]; then
    log_error "The following tools failed to install:"
    for t in "${failed[@]}"; do
        echo "  - $t"
    done
    exit 1
fi

chmod +x ./shoot.sh
echo -e "${GREEN}[OK] All tools installed successfully.${NC}"
