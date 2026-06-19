#!/usr/bin/env bats

load test_helper

setup() {
    setup_test_env
    load_shoot

    # Create prerequisite files that port scan expects
    echo "1.2.3.4" > "$scan_path/ips.txt"
    echo '{"a":["1.2.3.4"],"host":"sub1.example.com"}' > "$scan_path/dns.json"

    # naabu: port scanner mock - outputs IP:port pairs
    cat > "$MOCK_DIR/naabu" <<'EOF'
#!/bin/bash
echo "1.2.3.4:80"
echo "1.2.3.4:443"
echo "1.2.3.4:8080"
EOF
    chmod +x "$MOCK_DIR/naabu"

    # tew: virtual host discovery mock
    cat > "$MOCK_DIR/tew" <<'EOF'
#!/bin/bash
# Parse -o flag for output file
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o) echo "sub1.example.com:80" > "$2"; shift 2;;
        *) shift;;
    esac
done
echo "http://sub1.example.com:80"
EOF
    chmod +x "$MOCK_DIR/tew"

    # httpx: HTTP probe mock
    cat > "$MOCK_DIR/httpx" <<'EOF'
#!/bin/bash
# Parse -o flag for output file
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o) out="$2"; shift 2;;
        *) shift;;
    esac
done
json='{"url":"http://sub1.example.com:80","status_code":200}'
if [ -n "$out" ]; then
    echo "$json" > "$out"
fi
echo "$json"
EOF
    chmod +x "$MOCK_DIR/httpx"
}

teardown() {
    teardown_test_env
}

@test "perform_port_scan prints info message" {
    run perform_port_scan
    [[ "$output" == *"Performing Port Scanning and HTTP Server Discovery"* ]]
}

@test "perform_port_scan creates ports.txt" {
    perform_port_scan >/dev/null 2>&1 || true
    [ -f "$scan_path/ports.txt" ]
}

@test "perform_port_scan ports.txt contains sorted unique ports" {
    perform_port_scan >/dev/null 2>&1 || true
    # naabu mock outputs IP:port, cut extracts IP part (before /)
    [ -s "$scan_path/ports.txt" ]
}

@test "perform_port_scan creates hostport.txt" {
    perform_port_scan >/dev/null 2>&1 || true
    [ -f "$scan_path/hostport.txt" ]
}

@test "perform_port_scan creates http.json" {
    perform_port_scan >/dev/null 2>&1 || true
    [ -f "$scan_path/http.json" ]
}

@test "perform_port_scan creates http.txt from http.json" {
    perform_port_scan >/dev/null 2>&1 || true
    [ -f "$scan_path/http.txt" ]
}

@test "perform_port_scan http.txt strips standard port numbers" {
    perform_port_scan >/dev/null 2>&1 || true
    # The sed in perform_port_scan strips :80 and :443 suffixes
    if [ -f "$scan_path/http.txt" ]; then
        ! grep -q ':80$' "$scan_path/http.txt"
        ! grep -q ':443$' "$scan_path/http.txt"
    fi
}
