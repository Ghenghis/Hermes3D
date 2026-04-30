"""Pytest configuration: make `hermes3d` importable from 03_implementation/src/."""
from __future__ import annotations

import sys
from pathlib import Path

# 04_testing/pytest/conftest.py -> 04_testing/pytest -> 04_testing -> repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
