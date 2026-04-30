#!/usr/bin/env bash
# Hermes3D A.6 — emit a single signed proof bundle for the current build.
#
# Usage:
#   bash scripts/build-bundle.sh
#   bash scripts/build-bundle.sh --output 05_truth_proof/bundles/
#   bash scripts/build-bundle.sh --key-env-var HERMES3D_PROOF_KEY
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

python_bin="${PYTHON:-python3}"
if ! command -v "$python_bin" >/dev/null 2>&1; then
    python_bin="python"
fi

exec "$python_bin" "$repo_root/scripts/_build_bundle.py" "$@"
