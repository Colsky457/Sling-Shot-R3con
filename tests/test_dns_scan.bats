#!/usr/bin/env bats

load test_helper

setup() {
    setup_test_env
    load_shoot

    # Create mock tools for DNS scanning
    # subfinder: reads stdin domain, outputs subdomains
    cat > "$MOCK_DIR/subfinder" <<'EOF'
#!/bin/bash
while IFS= read -r domain; do
    echo "sub1.$domain"
    echo "sub2.$domain"
done
EOF
    chmod +x "$MOCK_DIR/subfinder"

    # anew: appends unique lines to a file, outputs new lines
    cat > "$MOCK_DIR/anew" <<'EOF'
#!/bin/bash
file="$1"
touch "$file"
while IFS= read -r line; do
    if ! grep -qxF "$line" "$file" 2>/dev/null; then
        echo "$line" >> "$file"
        echo "$line"
    fi
done
EOF
    chmod +x "$MOCK_DIR/anew"

    # shuffledns: outputs discovered subdomains
    cat > "$MOCK_DIR/shuffledns" <<'EOF'
#!/bin/bash
echo "www.example.com"
echo "mail.example.com"
EOF
    chmod +x "$MOCK_DIR/shuffledns"

    # puredns: resolves subdomains, writes to output file
    cat > "$MOCK_DIR/puredns" <<'EOF'
#!/bin/bash
# Parse -w flag for output file
while [[ $# -gt 0 ]]; do
    case "$1" in
        -w) echo "sub1.example.com" > "$2"; shift 2;;
        *) shift;;
    esac
done
echo "1"
EOF
    chmod +x "$MOCK_DIR/puredns"

    # dnsx: reads resolved domains, outputs JSON with A records
    cat > "$MOCK_DIR/dnsx" <<'EOF'
#!/bin/bash
# Parse -o flag for output file
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o) out="$2"; shift 2;;
        *) shift;;
    esac
done
json='{"a":["1.2.3.4"],"host":"sub1.example.com"}'
if [ -n "$out" ]; then
    echo "$json" > "$out"
fi
echo "$json"
EOF
    chmod +x "$MOCK_DIR/dnsx"

    # Ensure jq is available (it's a real tool, not mocked)
    # But mock it if not available
    if ! command -v jq &>/dev/null; then
        cat > "$MOCK_DIR/jq" <<'JQEOF'
#!/bin/bash
echo "1.2.3.4"
JQEOF
        chmod +x "$MOCK_DIR/jq"
    fi

    # Create resolved.txt that dnsx reads
    echo "sub1.example.com" > "$ppath/resolved.txt"
}

teardown() {
    teardown_test_env
}

@test "perform_dns_scan prints info message" {
    run perform_dns_scan
    [[ "$output" == *"Performing DNS Enumeration and Resolution"* ]]
}

@test "perform_dns_scan creates subs.txt" {
    perform_dns_scan >/dev/null 2>&1 || true
    [ -f "$scan_path/subs.txt" ]
}

@test "perform_dns_scan populates subs.txt with discovered subdomains" {
    perform_dns_scan >/dev/null 2>&1 || true
    [ -s "$scan_path/subs.txt" ]
}

@test "perform_dns_scan calls subfinder with roots.txt content" {
    # Track subfinder invocations
    cat > "$MOCK_DIR/subfinder" <<'EOF'
#!/bin/bash
echo "SUBFINDER_CALLED" >> /tmp/bats_subfinder_log
while IFS= read -r line; do
    echo "sub.$line"
done
EOF
    chmod +x "$MOCK_DIR/subfinder"

    perform_dns_scan >/dev/null 2>&1 || true
    [ -f /tmp/bats_subfinder_log ]
    rm -f /tmp/bats_subfinder_log
}

@test "perform_dns_scan creates dns.json output" {
    perform_dns_scan >/dev/null 2>&1 || true
    [ -f "$scan_path/dns.json" ]
}

@test "perform_dns_scan creates ips.txt" {
    perform_dns_scan >/dev/null 2>&1 || true
    [ -f "$scan_path/ips.txt" ]
}
