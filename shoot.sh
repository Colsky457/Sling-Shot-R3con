#!/bin/bash

print_banner() {
    printf '%s\n' \
        '##################################################################' \
        '     _____ _ _                _____ _           _     _____  ____    ' \
        '    / ____| (_)              / ____| |         | |   |  __ \|___ \   ' \
        '   | (___ | |_ _ __   __ _  | (___ | |__   ___ | |_  | |__) | __) |  ___ ___  _ __  ' \
        '    \___ \| | | '\''_ \ / _\` |  \___ \| '\''_ \ / _ \| __| |  _  / |__ < / __/ _ \| '\''_ \ ' \
        '    ____) | | | | | | (_| |  ____) | | | | (_) | |_  | | \ \ ___) | (_| (_) | | | |' \
        '   |_____/|_|_|_| |_|\__, | |_____/|_| |_|\___/ \__| |_|  \_|____/ \___\___/|_| |_|' \
        '                    __/ |                                                          ' \
        '                   |___/                                                           ' \
        '                 Automate Your Bug Bounty Sling Shot R3con            #' \
        '                 Created by: Haqq the Bounty Hunter                   #' \
        '                 https://github.com/haqqibrahim                       #' \
        '##################################################################' >&2
}

print_usage() {
    printf '%s\n' \
        "Usage: $0 <domain> [options]" \
        '' \
        'Examples:' \
        "  $0 example.com" \
        "  $0 example.com --dry-run" \
        "  $0 example.com --resume" >&2
}

print_banner

if [ "$#" -eq 0 ]; then
    print_usage
    exit 1
fi

exec python3 -m sling.cli scan "$@"
