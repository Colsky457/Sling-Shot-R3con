#!/usr/bin/env bats

load test_helper

setup() {
    setup_test_env
    load_shoot
    # Override sleep to avoid delays in tests
    sleep() { :; }
    export -f sleep
}

teardown() {
    teardown_test_env
}

@test "setup_scan creates scope directory" {
    local scope_path="$ppath/scope/$id"
    rm -rf "$scope_path"
    setup_scan "$id" >/dev/null 2>&1
    [ -d "$scope_path" ]
}

@test "setup_scan creates roots.txt in scope directory" {
    setup_scan "$id" >/dev/null 2>&1
    local scope_path="$ppath/scope/$id"
    [ -f "$scope_path/roots.txt" ]
}

@test "setup_scan writes domain id to roots.txt" {
    setup_scan "$id" >/dev/null 2>&1
    local scope_path="$ppath/scope/$id"
    local content="$(cat "$scope_path/roots.txt")"
    [ "$content" = "$id" ]
}

@test "setup_scan creates scan_path directory" {
    setup_scan "$id" >/dev/null 2>&1
    [ -d "$scan_path" ]
}

@test "setup_scan copies roots.txt to scan_path" {
    setup_scan "$id" >/dev/null 2>&1
    [ -f "$scan_path/roots.txt" ]
}

@test "setup_scan roots.txt in scan_path contains correct domain" {
    setup_scan "$id" >/dev/null 2>&1
    local content="$(cat "$scan_path/roots.txt")"
    [ "$content" = "$id" ]
}

@test "setup_scan prints banner output" {
    run setup_scan "$id"
    [[ "$output" == *"Sling Shot R3con"* ]]
}

@test "setup_scan prints info messages" {
    run setup_scan "$id"
    [[ "$output" == *"Creating scan folder"* ]]
    [[ "$output" == *"Creating roots file"* ]]
    [[ "$output" == *"Starting scan against root"* ]]
}

@test "setup_scan changes directory to scan_path" {
    setup_scan "$id" >/dev/null 2>&1
    [ "$(pwd)" = "$scan_path" ]
}
