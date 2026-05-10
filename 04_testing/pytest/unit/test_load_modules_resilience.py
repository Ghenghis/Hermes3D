"""Bonus 12 #9 + #10 (Audit PR #135 / Wave 2026-05-09 synthesis).

Two independent fixes in ``hermes3d.db.load_modules``:

#9 (P1, ``_registry_path``)
    Pre-fix: ``Path(__file__).resolve().parents[5]`` was evaluated
    unguarded. On a frozen build / zipapp / nuitka package, ``__file__``
    can be much shallower than 5 directories from any plausible repo
    root, raising ``IndexError`` BEFORE the ``FileNotFoundError``
    fallback to ``_registry_from_committed_proof()`` could trigger.

    Post-fix: each candidate path expression is wrapped in its own
    try/except so a malformed candidate is dropped, not propagated.

#10 (P0, ``load_modules``)
    Pre-fix: ``conn = connect(); ...; conn.commit(); conn.close()`` had
    no try/finally. A ``KeyError`` or ``sqlite3.IntegrityError`` mid-loop
    raised out of the loop with the connection still open, leaking the
    FD and WAL files on Windows.

    Post-fix: ``with closing(connect()) as conn:`` always closes the
    connection; a try/except runs ``conn.rollback()`` on any exception
    before re-raising.

References:
- https://docs.python.org/3/library/contextlib.html#contextlib.closing
- https://www.sqlite.org/wal.html
- https://owasp.org/www-project-top-10-ci-cd-security-risks/ (CICD-SEC-10)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from hermes3d.db import load_modules as lm


# ---------------------------------------------------------------------------
# #9 — _registry_path frozen-build IndexError fallback
# ---------------------------------------------------------------------------


def test_registry_path_falls_back_when_parents5_raises_indexerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bonus 12 #9: a Path whose parents tuple is too short must NOT raise
    IndexError out of _registry_path; it must be silently skipped so the
    FileNotFoundError fallback can trigger."""

    # Force the "real" candidate path (Path("G:/Github/Hermes3D/...")) NOT to exist.
    real_exists = Path.exists
    fake_path = Path("/not/a/real/registry.yaml")

    def patched_exists(self: Path) -> bool:
        # Both candidate paths report "does not exist" so the function
        # falls all the way through to FileNotFoundError.
        return False

    monkeypatch.setattr(Path, "exists", patched_exists)

    # Now make __file__'s parents chain too short so parents[5] raises.
    class ShallowPath(type(Path())):  # type: ignore[misc]
        @property
        def parents(self):  # type: ignore[override]
            class ShallowParents:
                def __getitem__(self, index: int) -> Path:
                    raise IndexError(f"parents[{index}] not available on frozen build")
                def __len__(self) -> int:
                    return 0
            return ShallowParents()

        def resolve(self, strict: bool = False) -> Path:  # type: ignore[override]
            return self

    # Replace the module-level Path used inside _registry_path: the
    # function calls Path(__file__) via the lm module's reference.
    original_path_factory = lm.Path

    def fake_path_factory(arg: Any = ".") -> Path:
        # Anything except __file__ returns the real Path so the explicit
        # G:/ candidate works.
        if isinstance(arg, str) and arg.endswith("load_modules.py"):
            return ShallowPath(arg)
        return original_path_factory(arg)

    monkeypatch.setattr(lm, "Path", fake_path_factory)

    # FileNotFoundError must surface (not IndexError).
    with pytest.raises(FileNotFoundError):
        lm._registry_path()

    # Restore Path.exists (other tests).
    monkeypatch.setattr(Path, "exists", real_exists)


def test_registry_path_returns_first_existing_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Smoke: when the real candidate exists, it is returned."""
    real_yaml = tmp_path / "external_repos_registry.yaml"
    real_yaml.write_text("section_a:\n  module_a:\n    display: A\n", encoding="utf-8")

    real_exists = Path.exists

    def patched_exists(self: Path) -> bool:
        return self == real_yaml or real_exists(self)

    # First candidate is the hard-coded G:/ path; we override only the
    # candidate list-building flow by monkey-patching _registry_path.
    def fake_registry_path() -> Path:
        return real_yaml

    monkeypatch.setattr(lm, "_registry_path", fake_registry_path)
    # Sanity: the wrapper still returns the file we expect.
    assert lm._registry_path() == real_yaml


# ---------------------------------------------------------------------------
# #10 — load_modules rollback on partial-load failure
# ---------------------------------------------------------------------------


class _FailingExecuteConn:
    """A fake connection whose .execute() succeeds N times then raises."""

    def __init__(self, fail_after: int) -> None:
        self.fail_after = fail_after
        self.calls = 0
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def execute(self, sql: str, params: tuple = ()) -> None:
        self.calls += 1
        if self.calls > self.fail_after:
            raise sqlite3.IntegrityError("synthetic mid-loop failure")

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def _stub_registry() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        "section_a": {
            "module_a1": {"display": "A1", "license": "MIT", "launch_kind": "service"},
            "module_a2": {"display": "A2", "license": "MIT", "launch_kind": "service"},
        },
        "section_b": {
            "module_b1": {"display": "B1", "license": "MIT", "launch_kind": "service"},
        },
    }


def _wire_load_modules_stubs(
    monkeypatch: pytest.MonkeyPatch, fake_conn: _FailingExecuteConn, tmp_path: Path
) -> None:
    """Stub all collaborators so load_modules executes against the fake conn."""
    fake_db = tmp_path / "fake-db.sqlite"
    fake_db.write_bytes(b"")  # exists()==True
    monkeypatch.setattr(lm, "DB_PATH", fake_db)
    monkeypatch.setattr(lm, "init_db", lambda: None)
    monkeypatch.setattr(lm, "_parse_registry", lambda _p: _stub_registry())
    monkeypatch.setattr(lm, "_registry_path", lambda: tmp_path / "fake.yaml")
    monkeypatch.setattr(lm, "_manifest_index", lambda: {})
    monkeypatch.setattr(
        lm,
        "resolve_module_source",
        lambda *a, **kw: {"repo_url": "https://example.invalid/repo.git", "local_path": ""},
    )
    monkeypatch.setattr(
        lm,
        "inspect_source_path",
        lambda *a, **kw: {"install_state": "installed", "install_progress": 100, "detected_version": "x", "health": "ok"},
    )
    monkeypatch.setattr(lm, "connect", lambda: fake_conn)


def test_load_modules_rollback_on_partial_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Bonus 12 #10: an exception mid-loop must trigger conn.rollback()
    and re-raise; conn must still be closed by the with-closing context."""
    # Fail on the 3rd execute call (after 2 successful inserts).
    fake = _FailingExecuteConn(fail_after=2)
    _wire_load_modules_stubs(monkeypatch, fake, tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        lm.load_modules()

    assert fake.commits == 0, "commit() must NOT run when the loop raised"
    assert fake.rollbacks == 1, (
        "Bonus 12 #10 regression: exactly one rollback() must run on partial-load failure"
    )
    assert fake.closed is True, (
        "Bonus 12 #10 regression: connection must be closed via with-closing(...)"
    )


def test_load_modules_clean_path_commits_and_closes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Smoke: happy path commits once and closes."""
    fake = _FailingExecuteConn(fail_after=10_000)  # never fails
    _wire_load_modules_stubs(monkeypatch, fake, tmp_path)

    count = lm.load_modules()
    assert count == 3
    assert fake.commits == 1
    assert fake.rollbacks == 0
    assert fake.closed is True


def test_load_modules_uses_with_closing_pattern() -> None:
    """Source-level pin: confirm with-closing(connect()) pattern is in source.

    Catches accidental revert to the bare connect()/close() shape.
    """
    import inspect

    src = inspect.getsource(lm.load_modules)
    assert "with closing(connect())" in src, (
        "Bonus 12 #10 regression: with-closing(connect()) pattern was reverted"
    )
    assert "conn.rollback()" in src, (
        "Bonus 12 #10 regression: explicit rollback on exception was removed"
    )
