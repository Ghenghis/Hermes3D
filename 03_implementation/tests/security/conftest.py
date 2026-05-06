"""Pytest configuration: make `hermes3d` importable from 03_implementation/src/.

Mirrors the bootstrap in 04_testing/pytest/conftest.py so `pytest -q
03_implementation/tests/security/` works from the repo root without any
external installation.
"""

from __future__ import annotations

import sys
from pathlib import Path

# 03_implementation/tests/security/conftest.py
#   -> 03_implementation/tests/security
#   -> 03_implementation/tests
#   -> 03_implementation
#   -> repo root
HERE = Path(__file__).resolve()
IMPL_ROOT = HERE.parent.parent.parent
SRC = IMPL_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
