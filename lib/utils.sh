#!/bin/bash
# Shared utility functions for Sling Shot R3con

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ─── Logging ──────────────────────────────────────────────────────────────────
log_info() {
    echo -e "${CYAN}[INFO] $*${NC}"
}

log_warn() {
    echo -e "${YELLOW}[INFO] $*${NC}"
}

log_error() {
    echo -e "${RED}[ERROR] $*${NC}"
}

log_success() {
    echo -e "${GREEN}$*${NC}"
}

# ─── Argument Validation ──────────────────────────────────────────────────────
# Usage: check_args "$#" "<usage_string>"
check_args() {
    local arg_count="$1"
    local usage_msg="$2"
    if [ "$arg_count" -eq 0 ]; then
        log_error "Usage: $usage_msg"
        exit 1
    fi
}

# ─── Directory Helpers ────────────────────────────────────────────────────────
# Usage: ensure_dir "/path/to/dir" "description"
ensure_dir() {
    local dir_path="$1"
    local description="${2:-directory}"
    log_info "Creating $description"
    mkdir -p "$dir_path"
}

# Usage: require_dir "/path/to/dir"
require_dir() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        log_error "Path doesn't exist: $dir_path"
        exit 1
    fi
}

# ─── Timing ───────────────────────────────────────────────────────────────────
# Usage: format_duration <seconds>
format_duration() {
    local seconds="$1"
    if [ "$seconds" -gt 59 ]; then
        echo "$(( seconds / 60 )) minutes"
    else
        echo "$seconds seconds"
    fi
}

# ─── Banner ───────────────────────────────────────────────────────────────────
print_banner() {
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
}
