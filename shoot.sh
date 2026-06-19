#!/bin/bash

# Set up scan_path globally
id="$1"
ppath="$(pwd)"
timestamp="$(date +%s)"
scan_path="$ppath/scans/$id-$timestamp"

# Function to create a scan folder and set up necessary files
setup_scan() {
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

    echo -e "${CYAN}[INFO] Creating scan folder for $id"
    mkdir -p "$scope_path"
    sleep 3

    echo -e "${CYAN}[INFO] Creating roots file for $id"
    echo "$id" > "$scope_path/roots.txt"

    if [ $# -eq 0 ]; then
        echo -e "${RED}[ERROR] Usage: $0 <folder_name>${NC}"
        exit 1
    fi

    # Exit if scope doesn't exist
    if [ ! -d "$scope_path" ]; then
        echo -e "${RED}[ERROR] Path doesn't exist${NC}"
        exit 1
    fi

    mkdir -p "$scan_path"
    cd "$scan_path"

    echo -e "${CYAN}[INFO] Starting scan against root"
    cat "$scope_path/roots.txt"
    cp -v "$scope_path/roots.txt" "$scan_path/roots.txt"
}


# Function to perform DNS enumeration and resolution
perform_dns_scan() {
    echo -e "${YELLOW}[INFO] Performing DNS Enumeration and Resolution${NC}"

    ## DNS Enumeration - Find Subdomains
    cat "$scan_path/roots.txt" | subfinder | anew "$scan_path/subs.txt"
    cat "$scan_path/roots.txt" | shuffledns -w "$ppath/lists/subdomains-top1million-20000.txt" -r "$ppath/lists/resolvers.txt" | anew "$scan_path/subs.txt" | wc -l

    ## DNS Resolution - Resolve discovered Subdomains
    puredns resolve "$scan_path/subs.txt" -r "$ppath/lists/resolvers.txt" -w "$ppath/resolved.txt" | wc -l
    dnsx -l "$scan_path/resolved.txt" -json -o "$scan_path/dns.json" | jq -r '.a?[]?' | anew "$scan_path/ips.txt" | wc -l
}

# Function to perform port scanning and HTTP server discovery using naabu
perform_port_scan() {
    echo -e "${YELLOW}[INFO] Performing Port Scanning and HTTP Server Discovery${NC}"

    ## Port scanning & HTTP Server Discovery using naabu
    naabu -iL "$scan_path/ips.txt" -p 1-65535 -silent | cut -d '/' -f 1 | sort -u > "$scan_path/ports.txt"
    tew -l "$scan_path/ports.txt" -dnsx "$scan_path/dns.json" --vhost -o "$scan_path/hostport.txt" | httpx -json -o "$scan_path/http.json"

    cat "$scan_path/http.json" | jq -r '.url' | sed -e 's/:80$//g' -e 's/:443$//g' | sort -u > "$scan_path/http.txt"
}

# Function to verify live targets from resolved hosts or IPs
perform_alive_scan() {
    echo -e "${YELLOW}[INFO] Performing Alive Scan${NC}"

    ## Probe resolved hostnames for live HTTP(S) services
    if [ -s "$scan_path/resolved.txt" ]; then
        httpx -l "$scan_path/resolved.txt" -silent -o "$scan_path/alive_hosts.txt"
    fi

    ## Probe raw IPs for live HTTP(S) services
    if [ -s "$scan_path/ips.txt" ]; then
        httpx -l "$scan_path/ips.txt" -silent | anew "$scan_path/alive_hosts.txt"
    fi

    echo -e "${CYAN}[INFO] Alive hosts saved to alive_hosts.txt ($(wc -l < "$scan_path/alive_hosts.txt") hosts)${NC}"
}

# Function to capture screenshots of discovered HTTP services
perform_screenshotting() {
    echo -e "${YELLOW}[INFO] Performing Screenshotting${NC}"

    ## Take screenshots of all discovered HTTP endpoints
    if [ -s "$scan_path/http.txt" ]; then
        mkdir -p "$scan_path/screenshots"
        gowitness scan file -f "$scan_path/http.txt" --screenshot-path "$scan_path/screenshots"
    else
        echo -e "${RED}[WARN] http.txt is empty or missing, skipping screenshotting${NC}"
    fi

    echo -e "${CYAN}[INFO] Screenshots saved to $scan_path/screenshots/${NC}"
}

# Function to perform technology fingerprinting on discovered services
perform_tech_fingerprinting() {
    echo -e "${YELLOW}[INFO] Performing Technology Fingerprinting${NC}"

    ## Re-probe HTTP endpoints with tech-detect to extend httpx output
    if [ -s "$scan_path/http.txt" ]; then
        httpx -l "$scan_path/http.txt" -td -server -title -status-code -json -o "$scan_path/tech.json"
        cat "$scan_path/tech.json" | jq -r 'select(.tech != null) | "\(.url) [\(.tech | join(", "))]"' > "$scan_path/tech.txt"
    else
        echo -e "${RED}[WARN] http.txt is empty or missing, skipping tech fingerprinting${NC}"
    fi

    echo -e "${CYAN}[INFO] Tech fingerprints saved to tech.json and tech.txt${NC}"
}

# Function to perform content/directory discovery on HTTP targets
perform_content_discovery() {
    echo -e "${YELLOW}[INFO] Performing Content Discovery${NC}"

    ## Fuzz directories and files against discovered HTTP endpoints
    if [ -s "$scan_path/http.txt" ]; then
        local wordlist="$ppath/lists/content-discovery.txt"
        if [ ! -f "$wordlist" ]; then
            echo -e "${RED}[WARN] Wordlist not found at $wordlist, skipping content discovery${NC}"
            return
        fi

        while IFS= read -r url; do
            ffuf -u "${url}/FUZZ" -w "$wordlist" -mc 200,204,301,302,307,403 -ac -sf -s | \
                sed "s|^|${url}/|" | anew "$scan_path/content.txt"
        done < "$scan_path/http.txt"
    else
        echo -e "${RED}[WARN] http.txt is empty or missing, skipping content discovery${NC}"
    fi

    echo -e "${CYAN}[INFO] Discovered paths saved to content.txt${NC}"
}

# Function to discover parameters from crawl output and JS files
perform_param_discovery() {
    echo -e "${YELLOW}[INFO] Performing Parameter Discovery${NC}"

    ## Extract parameters from crawl results
    if [ -s "$scan_path/crawl.txt" ]; then
        cat "$scan_path/crawl.txt" | unfurl keys | sort -u > "$scan_path/params.txt"
        cat "$scan_path/crawl.txt" | unfurl format '%s://%d%p?%q' | grep "?" | sort -u > "$scan_path/param_urls.txt"
    fi

    ## Extract parameters from discovered JavaScript URLs
    if [ -d "$scan_path/js" ]; then
        find "$scan_path/js" -name "*.js" -exec grep -ohE '[?&][a-zA-Z0-9_]+=' {} \; | \
            tr '?&' '\n' | sed 's/=$//' | sort -u | anew "$scan_path/params.txt"
    fi

    echo -e "${CYAN}[INFO] Parameters saved to params.txt ($(wc -l < "$scan_path/params.txt" 2>/dev/null || echo 0) params)${NC}"
}

# Function to export a summary report of all scan results
perform_report_export() {
    echo -e "${YELLOW}[INFO] Performing Report Export${NC}"

    local report="$scan_path/report.txt"

    {
        echo "======================================"
        echo " Sling Shot R3con - Scan Report"
        echo " Target: $id"
        echo " Date:   $(date)"
        echo "======================================"
        echo ""
        echo "[Subdomains]     $(wc -l < "$scan_path/subs.txt" 2>/dev/null || echo 0) found"
        echo "[Resolved]       $(wc -l < "$scan_path/resolved.txt" 2>/dev/null || echo 0) resolved"
        echo "[IPs]            $(wc -l < "$scan_path/ips.txt" 2>/dev/null || echo 0) unique IPs"
        echo "[Ports]          $(wc -l < "$scan_path/ports.txt" 2>/dev/null || echo 0) open ports"
        echo "[HTTP Services]  $(wc -l < "$scan_path/http.txt" 2>/dev/null || echo 0) services"
        echo "[Crawled URLs]   $(wc -l < "$scan_path/crawl.txt" 2>/dev/null || echo 0) URLs"
        echo "[Parameters]     $(wc -l < "$scan_path/params.txt" 2>/dev/null || echo 0) params"
        echo "[Content Paths]  $(wc -l < "$scan_path/content.txt" 2>/dev/null || echo 0) paths"
        echo ""
        echo "======================================"
        echo " Output Directory: $scan_path"
        echo "======================================"
    } | tee "$report"

    echo -e "${CYAN}[INFO] Report saved to $report${NC}"
}

# Function to perform crawling and JavaScript scraping
perform_crawling() {
    echo -e "${YELLOW}[INFO] Performing Crawling and JavaScript Scraping${NC}"

    # CRAWLING
    katana -s "$scan_path/http.txt" --json | grep "{" | jq -r '.output?' | tee "$scan_path/crawl.txt"

    ### JavaScript crawling
    cat "$scan_path/crawl.txt" | grep "\.js" | httpx -sr -srd js
}

# Define colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No Color

# Main script

# Check if an argument is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}[ERROR] Usage: $0 <folder_name>${NC}"
    exit 1
fi

# Set up the scan folder and necessary files
setup_scan "$1"

# Perform DNS enumeration and resolution
perform_dns_scan

# Perform port scanning and HTTP server discovery
perform_port_scan

# Verify live targets
perform_alive_scan

# Capture screenshots of HTTP services
perform_screenshotting

# Fingerprint technologies on discovered services
perform_tech_fingerprinting

# Run content/directory discovery
perform_content_discovery

# Perform crawling and JavaScript scraping
perform_crawling

# Discover parameters from crawl output and JS files
perform_param_discovery

# Export summary report
perform_report_export

# Calculate and display scan duration
end_time="$(date +%s)"
seconds="$(expr $end_time - $timestamp)"
time=" "

if [[ $seconds -gt 59 ]]; then
    minutes=$(expr $seconds / 60)
    time="$minutes minutes"
else
    time="$seconds seconds"
fi

echo -e "${GREEN}[$id] Scan took $time${NC}"
