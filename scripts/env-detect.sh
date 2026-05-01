#!/usr/bin/env bash
# Hermes3D — print env-detect report as JSON.
#
# Read-only: runs nvidia-smi --query-gpu, node --version, wmic (Windows only).
# No installs. No mutations. No network calls.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  "$PY" -c "import json; from hermes3d.env.detect import detect_env; print(json.dumps(detect_env().to_dict(), indent=2))"
