"""Bonus 12 finding #4 (Audit PR #135): defense-in-depth on _zip_dirty_entries.

Pre-fix: ``_zip_dirty_entries`` opened the dirty-files zip without
``allowZip64=True`` and used ``path.relative_to(repo)`` against an
un-resolved repo path, leaving open:

- silent truncation of dirty backups >4 GiB on Python builds without
  zip64 default
- ``ValueError`` aborts on symlinked repo checkouts
- a symlink in the dirty tree could resolve to a target outside the repo
  but still be written into the archive with an arcname computed from
  the symlink path (CWE-22 path traversal on extract)

Post-fix: ``allowZip64=True``, symlinks skipped, arcname computed against
``repo.resolve()``, and arcname asserted to be a pure relative path
(no absolute / drive-letter / parent-traversal components).

References:
- https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile
- https://cwe.mitre.org/data/definitions/22.html
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest
from hermes3d.api.routes import agent_updates


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo


# ---------------------------------------------------------------------------
# Happy-path: normal files round-trip cleanly
# ---------------------------------------------------------------------------


def test_zip_writes_normal_files_with_relative_arcname(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    f1 = repo / "src" / "a.txt"
    f1.parent.mkdir()
    f1.write_text("hello", encoding="utf-8")
    f2 = repo / "b.txt"
    f2.write_text("world", encoding="utf-8")
    target = tmp_path / "dirty.zip"
    agent_updates._zip_dirty_entries(repo, [f1, f2], target)
    with zipfile.ZipFile(target, "r") as archive:
        names = sorted(archive.namelist())
    # arcnames must be RELATIVE (no leading slash / drive letter)
    assert all(not Path(name).is_absolute() for name in names), (
        f"Arcnames must be relative; got {names!r}"
    )
    # Use forward slashes — zipfile normalizes path separators per spec.
    assert "b.txt" in names
    assert any(n.endswith("a.txt") for n in names)


def test_zip_no_paths_creates_no_archive(tmp_path: Path) -> None:
    """Empty paths list must short-circuit without creating an archive."""
    repo = _make_repo(tmp_path)
    target = tmp_path / "dirty.zip"
    agent_updates._zip_dirty_entries(repo, [], target)
    assert not target.exists(), "Empty paths must NOT produce a zero-entry archive"


# ---------------------------------------------------------------------------
# Hardening: symlinks skipped (CWE-22 / path traversal)
# ---------------------------------------------------------------------------


def _can_create_symlink(tmp_path: Path) -> bool:
    """Detect whether the test process can create OS-level symlinks.

    Windows requires either developer mode or admin; CI may lack the
    privilege. We skip rather than fail in that case.
    """
    try:
        target = tmp_path / "_symlink_probe_target"
        target.write_text("probe", encoding="utf-8")
        link = tmp_path / "_symlink_probe_link"
        link.symlink_to(target)
        link.unlink()
        target.unlink()
        return True
    except (OSError, NotImplementedError):
        return False


def test_zip_skips_symlinks(tmp_path: Path) -> None:
    """Symlinks must NOT appear in the archive even if their target exists."""
    if not _can_create_symlink(tmp_path):
        pytest.skip("Filesystem / privilege does not allow symlink creation")
    repo = _make_repo(tmp_path)
    real = repo / "real.txt"
    real.write_text("real-content", encoding="utf-8")
    link = repo / "link-to-real.txt"
    link.symlink_to(real)
    target = tmp_path / "dirty.zip"
    agent_updates._zip_dirty_entries(repo, [link, real], target)
    with zipfile.ZipFile(target, "r") as archive:
        names = archive.namelist()
    assert "real.txt" in names
    assert "link-to-real.txt" not in names, (
        "Symlinks must be skipped to avoid CWE-22 path-traversal on extract"
    )


def test_zip_skips_symlink_pointing_outside_repo(tmp_path: Path) -> None:
    """A symlink whose target lives outside the repo must be skipped."""
    if not _can_create_symlink(tmp_path):
        pytest.skip("Filesystem / privilege does not allow symlink creation")
    repo = _make_repo(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside-secret", encoding="utf-8")
    link = repo / "leak-link"
    link.symlink_to(outside)
    target = tmp_path / "dirty.zip"
    agent_updates._zip_dirty_entries(repo, [link], target)
    # Archive must be created but EMPTY of the symlink.
    assert target.exists()
    with zipfile.ZipFile(target, "r") as archive:
        names = archive.namelist()
    assert names == [], f"Outside-pointing symlink leaked into archive: {names!r}"


# ---------------------------------------------------------------------------
# Hardening: resolved-repo arcname
# ---------------------------------------------------------------------------


def test_zip_handles_symlinked_repo_root(tmp_path: Path) -> None:
    """When the repo path is itself a symlink, _zip_dirty_entries must not
    raise ValueError from relative_to. Pre-fix this aborted the backup.
    """
    if not _can_create_symlink(tmp_path):
        pytest.skip("Filesystem / privilege does not allow symlink creation")
    real_repo = tmp_path / "real-repo"
    real_repo.mkdir()
    (real_repo / ".git").mkdir()
    (real_repo / "data.txt").write_text("payload", encoding="utf-8")
    repo_link = tmp_path / "repo-link"
    repo_link.symlink_to(real_repo, target_is_directory=True)
    # Caller passes the symlinked path; arcname must compute against the
    # resolved path internally.
    target = tmp_path / "dirty.zip"
    file_via_link = repo_link / "data.txt"
    agent_updates._zip_dirty_entries(repo_link, [file_via_link], target)
    with zipfile.ZipFile(target, "r") as archive:
        names = archive.namelist()
    assert names == ["data.txt"], (
        f"Symlinked repo root must produce arcname 'data.txt', got {names!r}"
    )


def test_zip_skips_path_outside_repo(tmp_path: Path) -> None:
    """Caller bug: a path that resolves outside the repo must be silently
    dropped (not raise, not include).
    """
    repo = _make_repo(tmp_path)
    inside = repo / "inside.txt"
    inside.write_text("ok", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    target = tmp_path / "dirty.zip"
    agent_updates._zip_dirty_entries(repo, [inside, outside], target)
    with zipfile.ZipFile(target, "r") as archive:
        names = archive.namelist()
    assert names == ["inside.txt"], f"Out-of-repo path leaked: {names!r}"


# ---------------------------------------------------------------------------
# Hardening: allowZip64=True
# ---------------------------------------------------------------------------


def test_zip_uses_allowzip64(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Confirm allowZip64=True is passed to zipfile.ZipFile.

    Direct probe via a wrapper class — cheaper than building a >4 GiB
    fixture which would never run in CI.
    """
    repo = _make_repo(tmp_path)
    f = repo / "small.txt"
    f.write_text("x", encoding="utf-8")
    captured: dict[str, object] = {}
    real_zip = zipfile.ZipFile

    class CapturingZip(real_zip):  # type: ignore[misc]
        def __init__(self, file, mode="r", *args, **kwargs):
            captured["allowZip64"] = kwargs.get("allowZip64")
            captured["compression"] = kwargs.get("compression")
            super().__init__(file, mode, *args, **kwargs)

    monkeypatch.setattr(zipfile, "ZipFile", CapturingZip)
    monkeypatch.setattr(agent_updates.zipfile, "ZipFile", CapturingZip)
    target = tmp_path / "dirty.zip"
    agent_updates._zip_dirty_entries(repo, [f], target)
    assert captured.get("allowZip64") is True, (
        f"allowZip64 must be True; got {captured.get('allowZip64')!r}. "
        "Without it, dirty backups >4 GiB silently truncate on some builds."
    )
    assert captured.get("compression") == zipfile.ZIP_DEFLATED


# ---------------------------------------------------------------------------
# Smoke: the function does not raise on normal inputs
# ---------------------------------------------------------------------------


def test_zip_does_not_raise_on_pathological_components(
    tmp_path: Path,
) -> None:
    """Defense-in-depth: even an absolute Path passed by accident must be
    silently dropped, not raise.
    """
    repo = _make_repo(tmp_path)
    inside = repo / "ok.txt"
    inside.write_text("ok", encoding="utf-8")
    target = tmp_path / "dirty.zip"
    # Caller bug: pass an absolute path that can't even be made relative.
    agent_updates._zip_dirty_entries(repo, [inside, Path(sys.executable)], target)
    with zipfile.ZipFile(target, "r") as archive:
        names = archive.namelist()
    # Only the legitimate file should land in the archive.
    assert names == ["ok.txt"], f"Expected only 'ok.txt'; got {names!r}"
