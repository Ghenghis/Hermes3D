#!/usr/bin/env bash
# scripts/format.sh — apply ruff format to src/ and tests/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v ruff >/dev/null 2>&1; then
    echo "[FAIL] ruff not installed. pip install ruff" >&2
    exit 1
fi

echo "[format] running ruff format ..."
ruff format src tests
echo "[format] done."
