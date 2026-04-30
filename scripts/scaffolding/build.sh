#!/usr/bin/env bash
# scripts/build.sh — produce a production wheel under dist/.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

if ! python3 -c 'import build' 2>/dev/null; then
    echo "[build] installing build module ..."
    python3 -m pip install --user build
fi

rm -rf dist/ build/
echo "[build] python3 -m build --wheel ..."
python3 -m build --wheel

echo "[build] artifacts:"
ls -lh dist/

# SHA256 sidecars
for whl in dist/*.whl; do
    sha=$(sha256sum "$whl" | awk '{print $1}')
    echo "$sha  $(basename "$whl")" > "${whl}.sha256"
    echo "  sha256: $sha"
done
echo "[build] done."
