"""Phase 1 Task 10 — verify the stale pseudocode is now a deprecation stub.

Closes Phase 0 audit finding #1 (HIGH): the pseudocode used to describe a
schema that never matched the real registry. Running it now raises
SystemExit(2) with a redirect message.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
STUB = REPO_ROOT / "hermes3d_gui_contract_kit_v4.1" / "scripts" / "registry_validator_pseudocode.py"


def test_pseudocode_stub_exists():
    assert STUB.exists(), "deprecation stub missing"


def test_pseudocode_stub_exits_nonzero_with_redirect_message():
    r = subprocess.run(
        [sys.executable, str(STUB)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode != 0, "deprecated stub must fail loudly"
    assert "deprecated" in r.stderr.lower()
    assert "hermes3d.registry.validator" in r.stderr


def test_pseudocode_no_longer_imports_obsolete_schema():
    """The file body must no longer reference 'repositories' / 'repo_url'."""
    text = STUB.read_text(encoding="utf-8")
    assert "REQUIRED_FIELDS" not in text, "obsolete pseudocode must be removed"
    # Mentioning the old names in the deprecation message is fine; what we
    # forbid is the obsolete *code* that referenced them.
    assert "data.get(\"repositories\"" not in text
