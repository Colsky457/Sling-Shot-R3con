#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "requirements.sh exists" {
    [ -f "$REPO_ROOT/requirements.sh" ]
}

@test "requirements.sh is a valid bash script" {
    run bash -n "$REPO_ROOT/requirements.sh"
    [ "$status" -eq 0 ]
}

@test "requirements.sh installs subfinder" {
    grep -q "subfinder" "$REPO_ROOT/requirements.sh"
}

@test "requirements.sh installs shuffledns" {
    grep -q "shuffledns" "$REPO_ROOT/requirements.sh"
}

@test "requirements.sh installs puredns" {
    grep -q "puredns" "$REPO_ROOT/requirements.sh"
}

@test "requirements.sh installs dnsx" {
    grep -q "dnsx" "$REPO_ROOT/requirements.sh"
}

@test "requirements.sh installs tew" {
    grep -q "tew" "$REPO_ROOT/requirements.sh"
}

@test "requirements.sh installs katana" {
    grep -q "katana" "$REPO_ROOT/requirements.sh"
}

@test "requirements.sh installs httpx" {
    grep -q "httpx" "$REPO_ROOT/requirements.sh"
}

@test "requirements.sh makes shoot.sh executable" {
    grep -q "chmod +x ./shoot.sh" "$REPO_ROOT/requirements.sh"
}

@test "requirements.sh uses go install for all tools" {
    local count
    count=$(grep -c "go install" "$REPO_ROOT/requirements.sh")
    [ "$count" -ge 7 ]
}
