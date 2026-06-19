#!/bin/bash
# Shared test helper for BATS tests

# Source shoot.sh functions without executing main
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Create a temporary directory for each test
setup_test_env() {
    TEST_DIR="$(mktemp -d)"
    export ppath="$TEST_DIR"
    export id="example.com"
    export timestamp="$(date +%s)"
    export scan_path="$ppath/scans/$id-$timestamp"

    # Create required directory structure
    mkdir -p "$ppath/scope/$id"
    mkdir -p "$ppath/scans"
    mkdir -p "$ppath/lists"
    mkdir -p "$scan_path"

    # Create minimal list files
    echo "8.8.8.8" > "$ppath/lists/resolvers.txt"
    echo "www" > "$ppath/lists/subdomains-top1million-20000.txt"

    # Create roots.txt in scan_path (as setup_scan would)
    echo "$id" > "$scan_path/roots.txt"

    # Set up mock tools directory
    MOCK_DIR="$TEST_DIR/mocks"
    mkdir -p "$MOCK_DIR"
    export PATH="$MOCK_DIR:$PATH"
}

# Clean up the temporary directory after each test
teardown_test_env() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Create a mock executable that echoes its arguments or a fixed output
create_mock() {
    local name="$1"
    local output="${2:-}"
    local exit_code="${3:-0}"
    cat > "$MOCK_DIR/$name" <<EOF
#!/bin/bash
if [ -n "$output" ]; then
    echo "$output"
else
    cat  # pass through stdin
fi
exit $exit_code
EOF
    chmod +x "$MOCK_DIR/$name"
}

# Create a mock that reads stdin and writes fixed output
create_mock_with_stdin() {
    local name="$1"
    local output="${2:-}"
    cat > "$MOCK_DIR/$name" <<'OUTER'
#!/bin/bash
cat > /dev/null  # consume stdin
OUTER
    if [ -n "$output" ]; then
        echo "echo '$output'" >> "$MOCK_DIR/$name"
    fi
    chmod +x "$MOCK_DIR/$name"
}

# Source shoot.sh to load functions
load_shoot() {
    source "$REPO_ROOT/shoot.sh"
}
