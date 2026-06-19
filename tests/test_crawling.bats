#!/usr/bin/env bats

load test_helper

setup() {
    setup_test_env
    load_shoot

    # Create prerequisite http.txt that crawling expects
    echo "http://sub1.example.com" > "$scan_path/http.txt"

    # katana: web crawler mock
    cat > "$MOCK_DIR/katana" <<'EOF'
#!/bin/bash
echo '{"output":"http://sub1.example.com/page1"}'
echo '{"output":"http://sub1.example.com/app.js"}'
echo '{"output":"http://sub1.example.com/page2"}'
EOF
    chmod +x "$MOCK_DIR/katana"

    # httpx: HTTP probe mock for JS crawling
    cat > "$MOCK_DIR/httpx" <<'EOF'
#!/bin/bash
cat > /dev/null
EOF
    chmod +x "$MOCK_DIR/httpx"
}

teardown() {
    teardown_test_env
}

@test "perform_crawling prints info message" {
    run perform_crawling
    [[ "$output" == *"Performing Crawling and JavaScript Scraping"* ]]
}

@test "perform_crawling creates crawl.txt" {
    perform_crawling >/dev/null 2>&1 || true
    [ -f "$scan_path/crawl.txt" ]
}

@test "perform_crawling crawl.txt contains discovered URLs" {
    perform_crawling >/dev/null 2>&1 || true
    [ -s "$scan_path/crawl.txt" ]
}

@test "perform_crawling extracts URLs from katana JSON output" {
    perform_crawling >/dev/null 2>&1 || true
    grep -q "example.com" "$scan_path/crawl.txt"
}

@test "perform_crawling includes JavaScript files in crawl output" {
    perform_crawling >/dev/null 2>&1 || true
    grep -q "\.js" "$scan_path/crawl.txt"
}
