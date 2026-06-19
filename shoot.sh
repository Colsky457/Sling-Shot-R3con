#!/bin/bash
set -eo pipefail

# Define colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No Color

# Logging helpers
log_info()  { echo -e "${CYAN}[INFO] $*${NC}"; }
log_warn()  { echo -e "${YELLOW}[WARN] $*${NC}"; }
log_error() { echo -e "${RED}[ERROR] $*${NC}" >&2; }

# Verify that a command exists on PATH; exit with an error if it does not.
require_cmd() {
    if ! command -v "$1" &>/dev/null; then
        log_error "Required tool '$1' is not installed. Run requirements.sh first."
        exit 1
    fi
}

# Verify that a file exists; exit with an error if it does not.
require_file() {
    if [ ! -f "$1" ]; then
        log_error "Required file not found: $1"
        exit 1
    fi
}

# Set up scan_path globally
id="$1"
ppath="$(pwd)"
timestamp="$(date +%s)"
scan_path="$ppath/scans/$id-$timestamp"

# Function to create a scan folder and set up necessary files
setup_scan() {
    if [ -z "$1" ]; then
        log_error "Usage: $0 <domain>"
        exit 1
    fi

    local scope_path="$ppath/scope/$id"

    echo -e "${GREEN}##################################################################"
    echo -e "${GREEN}     _____ _ _                _____ _           _     _____  ____    "
    echo -e "${GREEN}    / ____| (_)              / ____| |         | |   |  __ \|___ \   "
    echo -e "${GREEN}   | (___ | |_ _ __   __ _  | (___ | |__   ___ | |_  | |__) | __) |  ___ ___  _ __  "
    echo -e "${GREEN}    \___ \| | | '_ \ / _\` |  \___ \| '_ \ / _ \| __| |  _  / |__ < / __/ _ \| '_ \ "
    echo -e "${GREEN}    ____) | | | | | | (_| |  ____) | | | | (_) | |_  | | \ \ ___) | (_| (_) | | | |"
    echo -e "${GREEN}   |_____/|_|_|_| |_|\__, | |_____/|_| |_|\___/ \__| |_|  \_|____/ \___\___/|_| |_|"
    echo -e "${GREEN}                    __/ |                                                          "
    echo -e "${GREEN}                   |___/                                                           "
    echo -e "${YELLOW}                 Automate Your Bug Bounty Sling Shot R3con            #"
    echo -e "${YELLOW}                 Created by: Haqq the Bounty Hunter                   #"
    echo -e "${YELLOW}                 https://github.com/haqqibrahim                       #"
    echo -e "${GREEN}##################################################################${NC}"

    log_info "Creating scan folder for $id"
    if ! mkdir -p "$scope_path"; then
        log_error "Failed to create scope directory: $scope_path"
        exit 1
    fi
    sleep 3

    log_info "Creating roots file for $id"
    echo "$id" > "$scope_path/roots.txt"

    if ! mkdir -p "$scan_path"; then
        log_error "Failed to create scan directory: $scan_path"
        exit 1
    fi

    if ! cd "$scan_path"; then
        log_error "Failed to change directory to: $scan_path"
        exit 1
    fi

    log_info "Starting scan against root"
    cat "$scope_path/roots.txt"
    cp -v "$scope_path/roots.txt" "$scan_path/roots.txt"
}


# Function to perform DNS enumeration and resolution
perform_dns_scan() {
    log_info "Performing DNS Enumeration and Resolution"

    require_file "$scan_path/roots.txt"
    require_file "$ppath/lists/subdomains-top1million-20000.txt"
    require_file "$ppath/lists/resolvers.txt"

    ## DNS Enumeration - Find Subdomains
    if ! subfinder < "$scan_path/roots.txt" | anew "$scan_path/subs.txt"; then
        log_error "subfinder failed during subdomain enumeration"
        return 1
    fi

    if ! shuffledns -w "$ppath/lists/subdomains-top1million-20000.txt" -r "$ppath/lists/resolvers.txt" < "$scan_path/roots.txt" | anew "$scan_path/subs.txt" | wc -l; then
        log_error "shuffledns failed during subdomain enumeration"
        return 1
    fi

    require_file "$scan_path/subs.txt"

    ## DNS Resolution - Resolve discovered Subdomains
    if ! puredns resolve "$scan_path/subs.txt" -r "$ppath/lists/resolvers.txt" -w "$scan_path/resolved.txt" | wc -l; then
        log_error "puredns failed during DNS resolution"
        return 1
    fi

    require_file "$scan_path/resolved.txt"

    if ! dnsx -l "$scan_path/resolved.txt" -json -o "$scan_path/dns.json" | jq -r '.a?[]?' | anew "$scan_path/ips.txt" | wc -l; then
        log_error "dnsx failed during DNS resolution"
        return 1
    fi
}

# Function to perform port scanning and HTTP server discovery using naabu
perform_port_scan() {
    log_info "Performing Port Scanning and HTTP Server Discovery"

    require_file "$scan_path/ips.txt"
    require_file "$scan_path/dns.json"

    ## Port scanning & HTTP Server Discovery using naabu
    if ! naabu -iL "$scan_path/ips.txt" -p 1-65535 -silent | cut -d '/' -f 1 | sort -u > "$scan_path/ports.txt"; then
        log_error "naabu failed during port scanning"
        return 1
    fi

    require_file "$scan_path/ports.txt"

    if ! tew -l "$scan_path/ports.txt" -dnsx "$scan_path/dns.json" --vhost -o "$scan_path/hostport.txt" | httpx -json -o "$scan_path/http.json"; then
        log_error "tew/httpx failed during HTTP server discovery"
        return 1
    fi

    require_file "$scan_path/http.json"

    if ! jq -r '.url' < "$scan_path/http.json" | sed -e 's/:80$//g' -e 's/:443$//g' | sort -u > "$scan_path/http.txt"; then
        log_error "Failed to extract URLs from HTTP scan results"
        return 1
    fi
}

# Function to perform crawling and JavaScript scraping
perform_crawling() {
    log_info "Performing Crawling and JavaScript Scraping"

    require_file "$scan_path/http.txt"

    # CRAWLING
    if ! katana -s "$scan_path/http.txt" --json | grep "{" | jq -r '.output?' | tee "$scan_path/crawl.txt"; then
        log_error "katana failed during crawling"
        return 1
    fi

    require_file "$scan_path/crawl.txt"

    ### JavaScript crawling
    if ! grep "\.js" "$scan_path/crawl.txt" | httpx -sr -srd js; then
        log_warn "No JavaScript files found or httpx failed during JS crawling"
    fi
}

# Main script

# Check if an argument is provided
if [ $# -eq 0 ]; then
    log_error "Usage: $0 <domain>"
    exit 1
fi

# Verify required external tools are available
for cmd in subfinder shuffledns puredns dnsx naabu tew httpx katana jq anew; do
    require_cmd "$cmd"
done

# Set up the scan folder and necessary files
setup_scan "$1"

# Perform DNS enumeration and resolution
if ! perform_dns_scan; then
    log_error "DNS scan stage failed — aborting."
    exit 1
fi

# Perform port scanning and HTTP server discovery
if ! perform_port_scan; then
    log_error "Port scan stage failed — aborting."
    exit 1
fi

# Perform crawling and JavaScript scraping
if ! perform_crawling; then
    log_error "Crawling stage failed — aborting."
    exit 1
fi

# Calculate and display scan duration
end_time="$(date +%s)"
seconds=$(( end_time - timestamp ))

if [[ $seconds -gt 59 ]]; then
    minutes=$(( seconds / 60 ))
    time="$minutes minutes"
else
    time="$seconds seconds"
fi

log_info "[$id] Scan completed successfully in $time"
