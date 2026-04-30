#!/usr/bin/env bash
# scripts/release.sh — produce a versioned release zip with checksums + proof envelope.
#
# Usage:
#   bash scripts/release.sh                # full release
#   bash scripts/release.sh --dry-run      # build artifact but don't sign
#   bash scripts/release.sh --version 5.1.0
#
# Outputs (under dist/release/<version>/):
#   hermes3d_os_lite_v<version>.zip
#   hermes3d_os_lite_v<version>.zip.sha256
#   hermes3d_os_lite_v<version>.proof.json

set -euo pipefail

DRY_RUN=0
VERSION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --version) VERSION="$2"; shift 2 ;;
        *) echo "[FAIL] unknown arg: $1"; exit 1 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Read version from pyproject.toml if not supplied
if [[ -z "$VERSION" ]]; then
    VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
fi

OUT_DIR="dist/release/$VERSION"
mkdir -p "$OUT_DIR"

ARTIFACT="$OUT_DIR/hermes3d_os_lite_v${VERSION}.zip"
echo "[release] packaging $ARTIFACT ..."

# Build the zip from a clean staging area
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

cp -r src tests config scripts pyproject.toml requirements.txt requirements-dev.txt env "$STAGE/"
[[ -f .gitignore ]] && cp .gitignore "$STAGE/"
[[ -f .editorconfig ]] && cp .editorconfig "$STAGE/"

(cd "$STAGE" && zip -qr "$REPO_ROOT/$ARTIFACT" .)

# SHA256 sidecar
ART_SHA=$(sha256sum "$ARTIFACT" | awk '{print $1}')
echo "$ART_SHA  $(basename "$ARTIFACT")" > "${ARTIFACT}.sha256"
echo "  sha256: $ART_SHA"
echo "  size:   $(stat -c%s "$ARTIFACT" 2>/dev/null || stat -f%z "$ARTIFACT") bytes"

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[release] dry-run; skipping proof envelope."
    exit 0
fi

# Proof envelope (HMAC-SHA256 signed)
PROOF="$OUT_DIR/hermes3d_os_lite_v${VERSION}.proof.json"
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
PYTHON_VER="$(python3 -c 'import sys; print(".".join(str(x) for x in sys.version_info[:3]))')"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
HOST_FP="$(hostname 2>/dev/null || echo 'unknown')"

PROOF_KEY="${HERMES3D_PROOF_KEY:-hermes3d-default-proof-key-not-secret}"

PYTHONPATH="$REPO_ROOT/src" python3 - <<PY
import hashlib, hmac, json, sys

doc = {
    "envelope_version": "1.0.0",
    "produced_at": "$NOW",
    "produced_by": {
        "tool": "scripts/release.sh",
        "git_commit": "$GIT_COMMIT",
        "python": "$PYTHON_VER",
        "host_fingerprint": "$HOST_FP",
    },
    "subject": {
        "kind": "release",
        "version": "$VERSION",
        "artifact": "$(basename "$ARTIFACT")",
    },
    "inputs": {
        "artifact_sha256": "$ART_SHA",
    },
    "decision": {
        "pass": True,
        "checks": [
            {"name": "artifact_built", "pass": True, "detail": "zip created"},
            {"name": "sha256_recorded", "pass": True, "detail": "$ART_SHA"},
        ],
    },
}
canonical = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
mac = hmac.new(b"$PROOF_KEY", canonical, hashlib.sha256).hexdigest()
doc["signature"] = {"algorithm": "HMAC-SHA256", "value": mac}
with open("$PROOF", "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
print(f"  proof:  {mac[:16]}...")
PY

echo "[release] done."
echo "  artifact: $ARTIFACT"
echo "  proof:    $PROOF"
