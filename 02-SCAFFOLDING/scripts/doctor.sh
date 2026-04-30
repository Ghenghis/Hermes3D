#!/usr/bin/env bash
# scripts/doctor.sh — environment prerequisite check (Linux / WSL)
# Exits non-zero if any required prerequisite fails.
#
# Usage:
#   bash scripts/doctor.sh           # human-readable
#   bash scripts/doctor.sh --json    # machine-readable

set -u

JSON_MODE=0
if [[ "${1:-}" == "--json" ]]; then
    JSON_MODE=1
fi

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
RESULTS=()

record() {
    local status="$1"      # PASS / WARN / FAIL
    local name="$2"
    local detail="$3"
    local fix="${4:-}"
    case "$status" in
        PASS) PASS_COUNT=$((PASS_COUNT + 1)) ;;
        WARN) WARN_COUNT=$((WARN_COUNT + 1)) ;;
        FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    esac
    RESULTS+=("${status}|${name}|${detail}|${fix}")
}

check_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        record FAIL "python3" "not found on PATH" "Install Python 3.11+ via your package manager"
        return
    fi
    local ver
    ver="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")')"
    local major minor
    major="$(echo "$ver" | cut -d. -f1)"
    minor="$(echo "$ver" | cut -d. -f2)"
    if [[ "$major" -lt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -lt 11 ]]; }; then
        record FAIL "python3" "$ver (need >=3.11)" "Install Python 3.11+ via your package manager"
    else
        record PASS "python3" "$ver" ""
    fi
}

check_pip_packages() {
    local pkgs=(trimesh numpy fastapi uvicorn pydantic httpx)
    local missing=()
    for pkg in "${pkgs[@]}"; do
        if ! python3 -c "import ${pkg}" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        record FAIL "python deps" "missing: ${missing[*]}" "pip install -r requirements.txt"
    else
        record PASS "python deps" "all 6 core packages present" ""
    fi
}

check_dev_packages() {
    local pkgs=(pytest)
    local missing=()
    for pkg in "${pkgs[@]}"; do
        if ! python3 -c "import ${pkg}" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        record WARN "dev deps" "missing: ${missing[*]} (only required for tests)" "pip install -r requirements-dev.txt"
    else
        record PASS "dev deps" "pytest present" ""
    fi
}

check_prusaslicer() {
    if command -v prusa-slicer >/dev/null 2>&1 || command -v PrusaSlicer >/dev/null 2>&1; then
        record PASS "PrusaSlicer" "found on PATH" ""
    elif command -v orcaslicer >/dev/null 2>&1 || command -v OrcaSlicer >/dev/null 2>&1; then
        record PASS "OrcaSlicer" "found on PATH (no PrusaSlicer)" ""
    else
        record WARN "slicer" "neither PrusaSlicer nor OrcaSlicer on PATH" "Install one for slicer integration tests"
    fi
}

check_disk_space() {
    local avail_kb
    avail_kb="$(df -k . | awk 'NR==2 {print $4}')"
    local avail_gb=$((avail_kb / 1024 / 1024))
    if [[ "$avail_gb" -lt 5 ]]; then
        record FAIL "disk space" "${avail_gb}GB free (need >=5GB)" "Free up disk space"
    elif [[ "$avail_gb" -lt 20 ]]; then
        record WARN "disk space" "${avail_gb}GB free (recommend >=20GB)" "20GB recommended for slicer cache + builds"
    else
        record PASS "disk space" "${avail_gb}GB free" ""
    fi
}

check_var_dir() {
    local var_dir="./var"
    if [[ ! -d "$var_dir" ]]; then
        if mkdir -p "$var_dir" 2>/dev/null; then
            record PASS "var dir" "created $var_dir" ""
        else
            record FAIL "var dir" "could not create $var_dir" "mkdir -p ./var (check permissions)"
        fi
    else
        record PASS "var dir" "exists" ""
    fi
}

check_proof_key() {
    if [[ -n "${HERMES3D_PROOF_KEY:-}" ]]; then
        record PASS "proof key" "HERMES3D_PROOF_KEY set" ""
    else
        record WARN "proof key" "HERMES3D_PROOF_KEY not set (using dev default)" "Set HERMES3D_PROOF_KEY in .env for production"
    fi
}

check_optional_gpu() {
    if command -v nvidia-smi >/dev/null 2>&1; then
        local name
        name="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
        if [[ -n "$name" ]]; then
            record PASS "gpu" "$name" ""
        else
            record WARN "gpu" "nvidia-smi present but no GPU detected" ""
        fi
    else
        record WARN "gpu" "nvidia-smi not on PATH (optional for LLM acceleration)" ""
    fi
}

check_optional_ollama() {
    if command -v curl >/dev/null 2>&1; then
        local url="${HERMES3D_LLM_BASE_URL:-http://127.0.0.1:11434}"
        if curl -fsS -m 1 "${url}/api/tags" >/dev/null 2>&1; then
            record PASS "ollama" "reachable at $url" ""
        else
            record WARN "ollama" "not reachable at $url (optional)" "Start ollama if you want LLM features"
        fi
    else
        record WARN "ollama" "curl not available, cannot probe" ""
    fi
}

# Run checks
check_python
check_pip_packages
check_dev_packages
check_prusaslicer
check_disk_space
check_var_dir
check_proof_key
check_optional_gpu
check_optional_ollama

# Output
if [[ "$JSON_MODE" -eq 1 ]]; then
    printf '{\n  "results": [\n'
    local first=1
    for r in "${RESULTS[@]}"; do
        IFS='|' read -r status name detail fix <<<"$r"
        if [[ "$first" -eq 1 ]]; then first=0; else printf ',\n'; fi
        printf '    {"status": "%s", "name": "%s", "detail": "%s", "fix": "%s"}' \
               "$status" "$name" "$detail" "$fix"
    done
    printf '\n  ],\n'
    printf '  "summary": {"pass": %d, "warn": %d, "fail": %d}\n' \
           "$PASS_COUNT" "$WARN_COUNT" "$FAIL_COUNT"
    printf '}\n'
else
    echo "Hermes3D-OS Lite — environment doctor"
    echo "======================================="
    for r in "${RESULTS[@]}"; do
        IFS='|' read -r status name detail fix <<<"$r"
        case "$status" in
            PASS) printf "  \033[32m[PASS]\033[0m %-20s %s\n" "$name" "$detail" ;;
            WARN) printf "  \033[33m[WARN]\033[0m %-20s %s\n" "$name" "$detail"
                  if [[ -n "$fix" ]]; then printf "         \033[2m%s\033[0m\n" "$fix"; fi ;;
            FAIL) printf "  \033[31m[FAIL]\033[0m %-20s %s\n" "$name" "$detail"
                  if [[ -n "$fix" ]]; then printf "         \033[2m%s\033[0m\n" "$fix"; fi ;;
        esac
    done
    echo
    echo "Summary: ${PASS_COUNT} pass, ${WARN_COUNT} warn, ${FAIL_COUNT} fail"
fi

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    exit 1
fi
exit 0
