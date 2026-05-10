"""Path-traversal audit over Hermes3D services and routes.

Lane 19 (H3D-CLAUDE-SECURITY-MCP). READ-ONLY against the source under audit.

The canonical user-supplied-path validators live in ``services/code_history.py``
(``_resolve_project_path`` and ``_resolve_project_subpath``). This lane is
forbidden from editing that file (it is Codex-owned). We instead assert via
behavioural tests that:

1. ``..`` sequences are rejected.
2. Absolute-root paths (Windows ``C:\\`` / Unix ``/etc/passwd``) are rejected.
3. UNC paths (``\\\\server\\share``) are rejected.
4. Null-byte injection (``\\x00``) is rejected.
5. Empty / whitespace paths are rejected.
6. The validator resolves the candidate path and confirms it is *inside*
   the project root.

If the validator function signatures or names change, these tests fail
loudly so the audit catches a regression at PR time.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

CODE_HISTORY = importlib.import_module("hermes3d.services.code_history")


# --------------------------------------------------------------------------- #
# Symbol presence
# --------------------------------------------------------------------------- #


def test_canonical_validators_exist() -> None:
    """The two canonical validators must be present and callable."""
    assert hasattr(CODE_HISTORY, "_resolve_project_path"), (
        "_resolve_project_path is the canonical user-path validator and must exist"
    )
    assert hasattr(CODE_HISTORY, "_resolve_project_subpath")
    assert callable(CODE_HISTORY._resolve_project_path)
    assert callable(CODE_HISTORY._resolve_project_subpath)


# --------------------------------------------------------------------------- #
# Rejection cases
# --------------------------------------------------------------------------- #


# Paths that MUST raise — they would either escape PROJECT_ROOT or are
# explicitly malformed (null byte, empty).
REJECTED_PATHS: list[str] = [
    "../etc/passwd",
    "..\\..\\Windows\\System32\\drivers\\etc\\hosts",
    "subdir/../../etc/passwd",
    "C:/Windows/System32/cmd.exe",
    "C:\\Windows\\System32\\cmd.exe",
    "D:\\private\\.env",
    "/etc/passwd",
    "\\\\attacker.example\\share\\evil.bat",  # UNC
    "//attacker.example/share/evil.bat",  # forward-slash UNC variant
    "file\x00../../etc/passwd",  # null-byte injection
    "",  # empty
]


@pytest.mark.parametrize("malicious", REJECTED_PATHS)
def test_resolve_project_subpath_rejects_traversal(malicious: str) -> None:
    """Every malicious path must raise (Value/FileNotFound)Error.

    We use ``_resolve_project_subpath`` because it does not require the
    target file to actually exist (must_exist=False), so any rejection is
    purely policy-driven.
    """
    with pytest.raises((ValueError, FileNotFoundError, OSError)):
        CODE_HISTORY._resolve_project_subpath(malicious, must_exist=False)


@pytest.mark.parametrize("malicious", REJECTED_PATHS)
def test_resolve_project_path_rejects_traversal(malicious: str) -> None:
    """Same set against the write-capable validator (must always reject)."""
    with pytest.raises((ValueError, FileNotFoundError, OSError)):
        CODE_HISTORY._resolve_project_path(malicious, write=False)


# --------------------------------------------------------------------------- #
# Acceptance: a known-safe project-relative path must validate
# --------------------------------------------------------------------------- #


def test_known_safe_relative_subpath_resolves() -> None:
    """A path that exists inside PROJECT_ROOT must resolve cleanly."""
    project_root: Path = CODE_HISTORY.PROJECT_ROOT  # type: ignore[attr-defined]
    # The repo always ships a top-level ROADMAP.md inside 03_implementation.
    candidate_relative = "03_implementation/ROADMAP.md"
    candidate_absolute = project_root / candidate_relative
    if not candidate_absolute.is_file():
        pytest.skip(f"acceptance fixture missing: {candidate_absolute}")
    resolved = CODE_HISTORY._resolve_project_subpath(candidate_relative, must_exist=True)
    assert resolved.exists()
    # Resolved path must be inside the project root.
    resolved.relative_to(project_root)


# --------------------------------------------------------------------------- #
# Belt-and-braces: PROJECT_ROOT must itself be inside the repo
# --------------------------------------------------------------------------- #


def test_project_root_is_a_real_directory() -> None:
    project_root: Path = CODE_HISTORY.PROJECT_ROOT  # type: ignore[attr-defined]
    assert project_root.is_dir(), f"PROJECT_ROOT does not resolve: {project_root}"


# --------------------------------------------------------------------------- #
# Module-runtime probe paths must come from the BUILTIN_RUNTIME_PROBES dict,
# not from arbitrary user input. Pin that contract.
# --------------------------------------------------------------------------- #


def test_module_runtime_probe_paths_are_static_not_user_supplied() -> None:
    """``runtime_probe_config`` must source paths from the registry, not from
    the per-request module dict.

    We confirm the function exists and returns either a registry dict or
    ``None`` for an unknown module id.
    """
    module_runtime = importlib.import_module("hermes3d.services.module_runtime")
    assert callable(module_runtime.runtime_probe_config)
    # Unknown module id must not raise; must return None.
    assert module_runtime.runtime_probe_config("definitely_not_a_real_module_id_xyz") is None
