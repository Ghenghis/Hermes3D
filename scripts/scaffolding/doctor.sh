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

JSON_CHECKS=()
JSON_FIX_HINTS=()

json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

env_bool() {
    local name="$1"
    local value="${!name:-}"
    case "$value" in
        1|true|TRUE|yes|YES|on|ON) printf 'true' ;;
        0|false|FALSE|no|NO|off|OFF) printf 'false' ;;
        *) printf '' ;;
    esac
}

json_add_check() {
    local id="$1"
    local ok="$2"
    local detail="$3"
    local hint="${4:-}"
    JSON_CHECKS+=("${id}|${ok}|${detail}")
    if [[ "$ok" == "false" && -n "$hint" ]]; then
        JSON_FIX_HINTS+=("$hint")
    fi
}

json_platform() {
    if [[ -n "${HERMES3D_DOCTOR_PLATFORM:-}" ]]; then
        printf '%s' "$HERMES3D_DOCTOR_PLATFORM"
        return
    fi
    case "$(uname -s 2>/dev/null || printf Linux)" in
        Darwin*) printf 'macos' ;;
        *) printf 'linux' ;;
    esac
}

json_check_python() {
    local ver="${HERMES3D_DOCTOR_PYTHON_VERSION:-}"
    if [[ -z "$ver" ]]; then
        if ! command -v python3 >/dev/null 2>&1; then
            json_add_check "python_3_11_or_12" "false" "python3 not found on PATH" \
                "Install Python 3.11 or 3.12"
            return
        fi
        ver="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")' 2>/dev/null || true)"
    fi
    local major minor
    major="$(printf '%s' "$ver" | cut -d. -f1)"
    minor="$(printf '%s' "$ver" | cut -d. -f2)"
    if [[ "$major" -gt 3 || ( "$major" == "3" && "$minor" -ge 11 ) ]]; then
        json_add_check "python_3_11_or_12" "true" "$ver"
    else
        json_add_check "python_3_11_or_12" "false" "${ver:-unknown} (need >=3.11)" \
            "Install Python 3.11 or newer"
    fi
}

json_check_port_8080() {
    local override
    override="$(env_bool HERMES3D_DOCTOR_PORT_8080_FREE)"
    if [[ -n "$override" ]]; then
        if [[ "$override" == "true" ]]; then
            json_add_check "port_8080_free" "true" "port 8080 available"
        else
            json_add_check "port_8080_free" "false" "port 8080 is in use" \
                "Stop the process using port 8080 or choose another port"
        fi
        return
    fi
    if command -v python3 >/dev/null 2>&1 && python3 - <<'PY' >/dev/null 2>&1
import socket
s = socket.socket()
try:
    s.bind(("127.0.0.1", 8080))
finally:
    s.close()
PY
    then
        json_add_check "port_8080_free" "true" "port 8080 available"
    else
        json_add_check "port_8080_free" "false" "port 8080 is in use or could not be probed" \
            "Stop the process using port 8080 or choose another port"
    fi
}

json_check_git() {
    local override
    override="$(env_bool HERMES3D_DOCTOR_GIT_PRESENT)"
    if [[ -n "$override" ]]; then
        if [[ "$override" == "true" ]]; then
            json_add_check "git_present" "true" "git found on PATH"
        else
            json_add_check "git_present" "false" "git not found on PATH" "Install git"
        fi
        return
    fi
    if command -v git >/dev/null 2>&1; then
        json_add_check "git_present" "true" "git found on PATH"
    else
        json_add_check "git_present" "false" "git not found on PATH" "Install git"
    fi
}

json_check_libgl() {
    local platform="$1"
    if [[ "$platform" != "linux" ]]; then
        json_add_check "libgl_present" "null" "skipped: not applicable on this platform"
        return
    fi
    local override
    override="$(env_bool HERMES3D_DOCTOR_LIBGL_PRESENT)"
    if [[ -n "$override" ]]; then
        if [[ "$override" == "true" ]]; then
            json_add_check "libgl_present" "true" "libGL present"
        else
            json_add_check "libgl_present" "false" "libGL not found" "Install libgl1"
        fi
        return
    fi
    if { command -v ldconfig >/dev/null 2>&1 && ldconfig -p 2>/dev/null | grep -q 'libGL\.so'; } ||
       [[ -e /usr/lib/x86_64-linux-gnu/libGL.so.1 ]] ||
       [[ -e /usr/lib64/libGL.so.1 ]]; then
        json_add_check "libgl_present" "true" "libGL present"
    else
        json_add_check "libgl_present" "false" "libGL not found" "Install libgl1"
    fi
}

emit_json_envelope() {
    local platform
    platform="$(json_platform)"
    json_add_check "wsl2_present" "null" "skipped: not applicable on this platform"
    json_add_check "kernel_version" "null" "skipped: not applicable on this platform"
    json_check_python
    json_check_port_8080
    json_check_libgl "$platform"
    json_check_git

    local ok="true"
    local entry check_ok
    for entry in "${JSON_CHECKS[@]}"; do
        IFS='|' read -r _ check_ok _ <<<"$entry"
        if [[ "$check_ok" == "false" ]]; then
            ok="false"
            break
        fi
    done

    printf '{\n'
    printf '  "json_schema_version": 1,\n'
    printf '  "platform": "%s",\n' "$(json_escape "$platform")"
    printf '  "checks": [\n'
    local first=1 id detail
    for entry in "${JSON_CHECKS[@]}"; do
        IFS='|' read -r id check_ok detail <<<"$entry"
        if [[ "$first" -eq 1 ]]; then first=0; else printf ',\n'; fi
        printf '    {"id": "%s", "ok": %s, "detail": "%s"}' \
            "$(json_escape "$id")" "$check_ok" "$(json_escape "$detail")"
    done
    printf '\n  ],\n'
    printf '  "ok": %s,\n' "$ok"
    printf '  "fix_hints": ['
    first=1
    local hint
    for hint in "${JSON_FIX_HINTS[@]}"; do
        if [[ "$first" -eq 1 ]]; then first=0; else printf ', '; fi
        printf '"%s"' "$(json_escape "$hint")"
    done
    printf ']\n'
    printf '}\n'
}

if [[ "$JSON_MODE" -eq 1 ]]; then
    emit_json_envelope
    exit 0
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
