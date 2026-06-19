#!/usr/bin/env bats

load test_helper

setup() {
    setup_test_env
    load_shoot
}

teardown() {
    teardown_test_env
}

@test "init_globals sets id from argument" {
    init_globals "target.com"
    [ "$id" = "target.com" ]
}

@test "init_globals sets ppath to current working directory" {
    local before_pwd="$(pwd)"
    init_globals "target.com"
    [ "$ppath" = "$before_pwd" ]
}

@test "init_globals sets timestamp to a numeric value" {
    init_globals "target.com"
    [[ "$timestamp" =~ ^[0-9]+$ ]]
}

@test "init_globals sets scan_path using ppath, id, and timestamp" {
    init_globals "target.com"
    [[ "$scan_path" == "$ppath/scans/target.com-"* ]]
}

@test "init_globals handles domain with subdomain" {
    init_globals "sub.target.com"
    [ "$id" = "sub.target.com" ]
    [[ "$scan_path" == *"sub.target.com"* ]]
}

@test "init_globals handles empty argument" {
    init_globals ""
    [ "$id" = "" ]
}
