#!/usr/bin/env bats

load test_helper

setup() {
    setup_test_env
    load_shoot
}

teardown() {
    teardown_test_env
}

@test "main returns 1 when no arguments provided" {
    run main
    [ "$status" -eq 1 ]
}

@test "main prints usage error when no arguments provided" {
    run main
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"folder_name"* ]]
}

@test "calculate_duration outputs seconds for short scans" {
    timestamp="$(date +%s)"
    id="test.com"
    run calculate_duration
    [[ "$output" == *"seconds"* ]]
    [[ "$output" == *"test.com"* ]]
}

@test "calculate_duration outputs minutes for scans over 59 seconds" {
    timestamp="$(( $(date +%s) - 120 ))"
    id="test.com"
    run calculate_duration
    [[ "$output" == *"minutes"* ]]
    [[ "$output" == *"test.com"* ]]
}

@test "calculate_duration shows 2 minutes for 120-second scan" {
    timestamp="$(( $(date +%s) - 120 ))"
    id="test.com"
    run calculate_duration
    [[ "$output" == *"2 minutes"* ]]
}

@test "calculate_duration shows seconds for 30-second scan" {
    timestamp="$(( $(date +%s) - 30 ))"
    id="test.com"
    run calculate_duration
    [[ "$output" == *"30 seconds"* ]] || [[ "$output" == *"31 seconds"* ]]
}

@test "color variables are defined" {
    [ -n "$GREEN" ]
    [ -n "$CYAN" ]
    [ -n "$YELLOW" ]
    [ -n "$RED" ]
    [ -n "$NC" ]
}

@test "shoot.sh is executable" {
    [ -x "$REPO_ROOT/shoot.sh" ]
}

@test "shoot.sh exits with error when run without arguments" {
    run "$REPO_ROOT/shoot.sh"
    [ "$status" -eq 1 ]
}
