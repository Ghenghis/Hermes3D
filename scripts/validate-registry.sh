#!/usr/bin/env bash
# Hermes3D — wrapper for the production registry validator.
#
# Forwards all arguments to `python -m hermes3d.registry.validator`. The default
# (no args) validates the kit's external_repos_registry.yaml.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  "$PY" -m hermes3d.registry.validator "$@"
