#!/bin/bash
set -euo pipefail

# Check for Go
if ! command -v go &> /dev/null; then
    echo "[ERROR] Go is not installed. Install Go first: https://go.dev/dl/"
    exit 1
fi

# Check for jq (not a Go tool)
if ! command -v jq &> /dev/null; then
    echo "[INFO] Installing jq..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y jq
    elif command -v brew &> /dev/null; then
        brew install jq
    else
        echo "[ERROR] Could not install jq automatically. Please install it manually."
        exit 1
    fi
fi

echo "[INFO] Installing Go-based tools..."

go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest
go install -v github.com/d3mondev/puredns/v2@latest
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/pry0cc/tew@latest
go install -v github.com/tomnomnom/anew@latest

chmod +x ./shoot.sh

echo "[INFO] All dependencies installed successfully."
