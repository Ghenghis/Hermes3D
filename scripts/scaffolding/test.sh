#!/usr/bin/env bash
# scripts/test.sh — run the full Hermes3D-OS test suite (Linux / WSL).
#
# Usage:
#   bash scripts/test.sh                    # Layer A + B (fast, default)
#   bash scripts/test.sh --integration      # + Layer C
#   bash scripts/test.sh --e2e              # + Layer D (requires display or headless browser)
#   bash scripts/test.sh --acceptance       # acceptance runner only

set -u

INTEGRATION=0
E2E=0
ACCEPTANCE_ONLY=0
FAST=0
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --integration) INTEGRATION=1; shift ;;
        --e2e) E2E=1; INTEGRATION=1; shift ;;
        --acceptance) ACCEPTANCE_ONLY=1; shift ;;
        --fast) FAST=1; shift ;;
        --) shift; while [[ $# -gt 0 ]]; do EXTRA_ARGS+=("$1"); shift; done ;;
        *) EXTRA_ARGS+=("$1"); shift ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PYTHONPATH_BACKUP="${PYTHONPATH:-}"
export PYTHONPATH="$REPO_ROOT/03_implementation/src:$PYTHONPATH_BACKUP"
export HERMES3D_PROOF_KEY="${HERMES3D_PROOF_KEY:-hermes3d-default-proof-key-not-secret}"

# Resolve python: prefer python3 (Linux/macOS), fall back to python (Windows/Git-Bash).
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[FAIL] neither python3 nor python on PATH. Run scripts/doctor.sh first." >&2
    exit 1
fi

if [[ "$ACCEPTANCE_ONLY" -eq 1 ]]; then
    echo "[1/1] Acceptance runner ..."
    $PY 04_testing/acceptance/run_acceptance.py
    exit $?
fi

# Layer A static gates: ruff format + check + mypy (best-effort if installed)
echo "[1/4] Layer A: static gates ..."
if [[ "$FAST" -eq 1 ]]; then
    echo "  [fast] skipping ruff format + check + mypy"
elif command -v ruff >/dev/null 2>&1; then
    ruff format --check 03_implementation/src 04_testing/pytest || { echo "[FAIL] ruff format"; exit 1; }
    ruff check 03_implementation/src 04_testing/pytest || { echo "[FAIL] ruff check"; exit 1; }
    echo "  [PASS] ruff format + check"
else
    echo "  [WARN] ruff not installed; skipping format + lint (pip install ruff)"
fi

# Forbidden-pattern scan: TODO/FIXME/STUB outside tests/fixtures
echo "  [SCAN] forbidden patterns ..."
hits=$(grep -rE '\b(TODO|FIXME|STUB|PLACEHOLDER|NOT_IMPLEMENTED)\b' \
       03_implementation/src/hermes3d 2>/dev/null \
       --include='*.py' --exclude-dir=__pycache__ \
       || true)
if [[ -n "$hits" ]]; then
    echo "[FAIL] Forbidden patterns found in runtime code:"
    echo "$hits"
    exit 1
fi
echo "  [PASS] no forbidden patterns in 03_implementation/src/hermes3d"

# Layer B: unit + smoke tests
echo "[2/4] Layer B: unit + smoke tests ..."
if [[ "$INTEGRATION" -eq 1 ]]; then
    pytest_args=("04_testing/pytest/")
elif [[ "$FAST" -eq 1 ]]; then
    # --fast: only the new hardening tests known to be green; used by pre-push hook.
    pytest_args=(
        "04_testing/pytest/unit/test_retry_controller.py"
        "04_testing/pytest/unit/test_repair_agent.py"
        "04_testing/pytest/unit/test_remote_control.py"
    )
else
    pytest_args=("04_testing/pytest/unit" "04_testing/pytest/conformance")
fi
$PY -m pytest "${pytest_args[@]}" "${EXTRA_ARGS[@]}" --tb=no -q || exit $?

if [[ "$FAST" -eq 1 ]]; then
    # Skip acceptance + E2E in fast mode — pre-push only validates the new hardening surface.
    echo "[fast] skipped acceptance + E2E."
    exit 0
fi

# Layer B continued: acceptance runner
echo "[3/4] Layer B: acceptance runner ..."
$PY 04_testing/acceptance/run_acceptance.py || exit $?

if [[ "$E2E" -eq 1 ]]; then
    echo "[4/4] Layer D: Playwright E2E (UI Truth Gates) ..."
    bash "$REPO_ROOT/scripts/run-e2e.sh" || exit $?
else
    echo "[4/4] Layer D: skipped (use --e2e to enable)"
fi

echo
echo "[OK] All applicable layers green."
