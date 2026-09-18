#!/bin/bash

# ASCII-art banner (preserved for familiarity)
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No Color

# Print banner to stderr so it doesn't interfere with stdout piping
cat >&2 <<'EOF'
##################################################################
     _____ _ _                _____ _           _     _____  ____    
    / ____| (_)              / ____| |         | |   |  __ \|___ \   
   | (___ | |_ _ __   __ _  | (___ | |__   ___ | |_  | |__) | __) |  ___ ___  _ __  
    \___ \| | | '_ \ / _` |  \___ \| '_ \ / _ \| __| |  _  / |__ < / __/ _ \| '_ \ 
    ____) | | | | | | (_| |  ____) | | | | (_) | |_  | | \ \ ___) | (_| (_) | | | |
   |_____/|_|_|_| |_|\__, | |_____/|_| |_|\___/ \__| |_|  \_\____/ \___\___/|_| |_|
                    __/ |                                                         
                   |___/                                                          
                 Automate Your Bug Bounty Sling Shot R3con            #
                 Created by: Haqq the Bounty Hunter                   #
                 https://github.com/haqqibrahim                       #
##################################################################
EOF

# Check if an argument is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}[ERROR] Usage: $0 <domain> [options...]${NC}" >&2
    echo -e "${CYAN}Options: --resume, --dry-run, etc. (forwarded to sling CLI)${NC}" >&2
    exit 1
fi

# Delegate to Python CLI
exec python3 -m sling.cli scan "$@"
