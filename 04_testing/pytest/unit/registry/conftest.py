"""Shared fixtures for registry tests."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_path():
    """Return a callable that resolves a fixture filename to its absolute path."""

    def _load(name: str) -> Path:
        path = FIXTURE_DIR / name
        assert path.exists(), f"missing fixture: {name}"
        return path

    return _load
