#!/usr/bin/env bash
# scripts/lint.sh — Layer A static gates (ruff check + forbidden-pattern scan,
# optional mypy). Exits non-zero on any failure.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

FAILURES=0

# ruff check
if command -v ruff >/dev/null 2>&1; then
    echo "[lint] ruff check ..."
    if ! ruff check 03_implementation/src 04_testing/pytest; then
        FAILURES=$((FAILURES + 1))
    fi
    echo "[lint] ruff format --check ..."
    if ! ruff format --check 03_implementation/src 04_testing/pytest; then
        FAILURES=$((FAILURES + 1))
    fi
else
    echo "[WARN] ruff not installed — install with: pip install ruff" >&2
fi

# mypy strict (best-effort)
if command -v mypy >/dev/null 2>&1; then
    echo "[lint] mypy --strict 03_implementation/src/hermes3d ..."
    if ! mypy --strict --no-incremental 03_implementation/src/hermes3d 2>&1 | tail -50; then
        echo "[WARN] mypy reported issues (allowed during v5 hardening; see HONESTY_LEDGER)"
        # Do not increment FAILURES yet — v5.1 promotion goal
    fi
else
    echo "[WARN] mypy not installed — install with: pip install mypy" >&2
fi

# Forbidden-pattern scan
echo "[lint] forbidden-pattern scan ..."
hits=$(grep -rE '\b(TODO|FIXME|STUB|PLACEHOLDER|NOT_IMPLEMENTED)\b' \
       03_implementation/src/hermes3d 2>/dev/null \
       --include='*.py' --exclude-dir=__pycache__ \
       || true)
if [[ -n "$hits" ]]; then
    echo "[FAIL] Forbidden patterns found:"
    echo "$hits"
    FAILURES=$((FAILURES + 1))
fi

if [[ "$FAILURES" -gt 0 ]]; then
    echo "[FAIL] $FAILURES lint failure(s)."
    exit 1
fi
echo "[OK] lint passed."
