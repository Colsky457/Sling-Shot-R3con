#!/bin/bash

# Source shared utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"

# Validate arguments before anything else
check_args "$#" "$0 <domain>"

# Set up scan_path globally
id="$1"
ppath="$SCRIPT_DIR"
timestamp="$(date +%s)"
scan_path="$ppath/scans/$id-$timestamp"

# Function to create a scan folder and set up necessary files
setup_scan() {
    local scope_path="$ppath/scope/$id"

    print_banner

    ensure_dir "$scope_path" "scan folder for $id"
    sleep 3

    log_info "Creating roots file for $id"
    echo "$id" > "$scope_path/roots.txt"

    require_dir "$scope_path"

    ensure_dir "$scan_path" "output directory"
    cd "$scan_path"

    log_info "Starting scan against root"
    cat "$scope_path/roots.txt"
    cp -v "$scope_path/roots.txt" "$scan_path/roots.txt"
}

# Function to perform DNS enumeration and resolution
perform_dns_scan() {
    log_warn "Performing DNS Enumeration and Resolution"

    ## DNS Enumeration - Find Subdomains
    cat "$scan_path/roots.txt" | subfinder | anew "$scan_path/subs.txt"
    cat "$scan_path/roots.txt" | shuffledns -w "$ppath/lists/subdomains-top1million-20000.txt" -r "$ppath/lists/resolvers.txt" | anew "$scan_path/subs.txt" | wc -l

    ## DNS Resolution - Resolve discovered Subdomains
    puredns resolve "$scan_path/subs.txt" -r "$ppath/lists/resolvers.txt" -w "$ppath/resolved.txt" | wc -l
    dnsx -l "$scan_path/resolved.txt" -json -o "$scan_path/dns.json" | jq -r '.a?[]?' | anew "$scan_path/ips.txt" | wc -l
}

# Function to perform port scanning and HTTP server discovery using naabu
perform_port_scan() {
    log_warn "Performing Port Scanning and HTTP Server Discovery"

    ## Port scanning & HTTP Server Discovery using naabu
    naabu -iL "$scan_path/ips.txt" -p 1-65535 -silent | cut -d '/' -f 1 | sort -u > "$scan_path/ports.txt"
    tew -l "$scan_path/ports.txt" -dnsx "$scan_path/dns.json" --vhost -o "$scan_path/hostport.txt" | httpx -json -o "$scan_path/http.json"

    cat "$scan_path/http.json" | jq -r '.url' | sed -e 's/:80$//g' -e 's/:443$//g' | sort -u > "$scan_path/http.txt"
}

# Function to perform crawling and JavaScript scraping
perform_crawling() {
    log_warn "Performing Crawling and JavaScript Scraping"

    # CRAWLING
    katana -s "$scan_path/http.txt" --json | grep "{" | jq -r '.output?' | tee "$scan_path/crawl.txt"

    ### JavaScript crawling
    cat "$scan_path/crawl.txt" | grep "\.js" | httpx -sr -srd js
}

# Main script

# Set up the scan folder and necessary files
setup_scan "$1"

# Perform DNS enumeration and resolution
perform_dns_scan

# Perform port scanning and HTTP server discovery
perform_port_scan

# Perform crawling and JavaScript scraping
perform_crawling

# Calculate and display scan duration
end_time="$(date +%s)"
seconds="$(( end_time - timestamp ))"
time="$(format_duration "$seconds")"

log_success "[$id] Scan took $time"
