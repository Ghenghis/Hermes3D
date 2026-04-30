#!/usr/bin/env bash
# Hermes3D Preflight — validates the dev environment against contract requirements.
# Emits a JSON capability report to var/preflight/<utc>.json and human summary to stdout.
# Exit 0 = ready, 1 = blockers found.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="var/preflight"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/${UTC}.json"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yel()   { printf "\033[33m%s\033[0m\n" "$*"; }

REQUIRED_OK=1
declare -A CAP=()

check() {
  local name="$1"; local cmd="$2"; local required="$3"
  local ver=""
  if command -v "$cmd" >/dev/null 2>&1; then
    ver="$($cmd --version 2>&1 | head -1 | tr -d '\r')"
    CAP[$name]="present|$ver"
    green "  [OK] $name → $ver"
  else
    CAP[$name]="missing"
    if [[ "$required" == "yes" ]]; then
      red   "  [MISS] $name (REQUIRED)"
      REQUIRED_OK=0
    else
      yel   "  [opt] $name (optional, skipped)"
    fi
  fi
}

echo
echo "===== Hermes3D Preflight ($UTC) ====="
echo
echo "Required tools:"
check python  python  yes
check git     git     yes
check node    node    yes

echo
echo "Optional tools (enable extra capabilities):"
check pip            pip            no
check pytest         pytest         no
check ruff           ruff           no
check mypy           mypy           no
check npx            npx            no
check blender        blender        no
check ollama         ollama         no
# LM Studio: HTTP probe (no `lms` CLI required)
LMSTUDIO_URL="${LMSTUDIO_BASE_URL:-http://localhost:1234/v1}"
if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 2 "${LMSTUDIO_URL%/v1}/v1/models" >/dev/null 2>&1; then
  CAP[lmstudio]="present|reachable at $LMSTUDIO_URL"
  green "  [OK] lmstudio → reachable at $LMSTUDIO_URL"
else
  CAP[lmstudio]="missing"
  yel   "  [opt] lmstudio (not reachable at $LMSTUDIO_URL; start: lms server start)"
fi
check prusa-slicer   prusa-slicer   no
check orca-slicer    orca-slicer    no
check gh             gh             no

# Python version detail (need >= 3.11)
PY_OK=0
if command -v python >/dev/null 2>&1; then
  PYV="$(python -c 'import sys;print(".".join(map(str,sys.version_info[:3])))' 2>/dev/null || echo 0.0.0)"
  PY_MAJOR="$(echo "$PYV" | cut -d. -f1)"
  PY_MINOR="$(echo "$PYV" | cut -d. -f2)"
  if (( PY_MAJOR > 3 )) || (( PY_MAJOR == 3 && PY_MINOR >= 11 )); then
    PY_OK=1
    green "  [OK] Python $PYV >= 3.11"
  else
    red   "  [BAD] Python $PYV < 3.11"
    REQUIRED_OK=0
  fi
fi

# Git config sanity (we don't want to push to main accidentally)
HOOKS_PATH="$(git config --get core.hooksPath 2>/dev/null || true)"
if [[ "$HOOKS_PATH" == ".githooks" ]]; then
  green "  [OK] core.hooksPath = .githooks (pre-push guard active)"
else
  yel   "  [WARN] core.hooksPath not set; run scripts/install-hooks.sh"
fi

# Emit JSON
{
  echo "{"
  echo "  \"timestamp_utc\": \"$UTC\","
  echo "  \"required_ok\": $([[ $REQUIRED_OK -eq 1 ]] && echo true || echo false),"
  echo "  \"python_version\": \"${PYV:-unknown}\","
  echo "  \"hooks_path\": \"${HOOKS_PATH:-unset}\","
  echo "  \"capabilities\": {"
  first=1
  for k in "${!CAP[@]}"; do
    [[ $first -eq 0 ]] && echo ","
    first=0
    val="${CAP[$k]}"
    state="${val%%|*}"
    detail="${val#*|}"; [[ "$detail" == "$val" ]] && detail=""
    printf "    \"%s\": {\"state\": \"%s\", \"detail\": \"%s\"}" "$k" "$state" "${detail//\"/\\\"}"
  done
  echo
  echo "  }"
  echo "}"
} > "$OUT"

echo
echo "Report written: $OUT"
echo
if [[ $REQUIRED_OK -eq 1 ]]; then
  green "Preflight OK"
  exit 0
else
  red "Preflight FAILED — install missing required tools, then re-run."
  exit 1
fi
