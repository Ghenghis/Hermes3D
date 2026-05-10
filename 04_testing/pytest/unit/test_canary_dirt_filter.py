"""Unit tests for ``services/canary_dirt_filter``.

The W6-1 brief calls for ~5 tests covering the v0.13 canary scenario:
``.venv-canary/`` + ``_pip_install.log`` are untracked but must NOT flip the
``dirty`` flag, while a real edit to a tracked file MUST. We extend the suite
to nine tests so the filter is also exercised against:

- single-path predicate ``is_noise_path``
- the rename / copy porcelain shape ``XY orig -> dest``
- mixed real-edit + noise lines
- empty input
- nested / deep noise paths (e.g. ``.venv-canary/lib/site-packages/foo.py``)
- Windows-style backslash paths (defensive normalisation)

References (per brief constraint "2 sources"):
- ``git status --porcelain`` short-format spec:
  https://git-scm.com/docs/git-status#_short_format
- ``pathlib`` / regex-based path filtering for noise detection:
  https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.match
"""

from __future__ import annotations

import pytest

from hermes3d.services.canary_dirt_filter import (
    NOISE_PATTERNS,
    compute_dirty,
    filter_noise_lines,
    filter_path_list,
    is_noise_path,
)


CANARY_PORCELAIN = "?? .venv-canary/\n?? _pip_install.log\n"
"""The exact porcelain blob ``git status --short`` produces against the
v0.13 canary checkout after a fresh ``pip install -e .`` (verified via
``git status --porcelain`` at G:/Github/hermes-agent-v013-canary on
2026-05-09)."""


def test_canary_only_noise_reports_clean() -> None:
    """The canary scenario from the W6-1 brief: only venv + pip log dirt.

    A checkout whose ``git status --porcelain`` output contains nothing
    except ``.venv-canary/`` and ``_pip_install.log`` MUST be reported as
    ``dirty=False`` because every entry is filesystem noise outside
    version control.
    """
    dirty, surviving = compute_dirty(CANARY_PORCELAIN)
    assert dirty is False
    assert surviving == []


def test_real_edit_alone_reports_dirty() -> None:
    """A modification to a tracked file MUST keep dirty=True.

    Regression guard: the filter must NOT mask actual edits — only pip /
    pytest / venv / coverage / setuptools artifacts.
    """
    porcelain = " M 03_implementation/src/hermes3d/api/routes/agent_updates.py\n"
    dirty, surviving = compute_dirty(porcelain)
    assert dirty is True
    assert surviving == [" M 03_implementation/src/hermes3d/api/routes/agent_updates.py"]


def test_mixed_noise_and_real_edit_keeps_dirty() -> None:
    """Real edits beside venv/pip noise still report dirty.

    The surviving entries list must contain ONLY the real edit lines so
    operators see what actually needs attention.
    """
    porcelain = (
        "?? .venv-canary/\n"
        "?? _pip_install.log\n"
        " M 03_implementation/src/hermes3d/services/code_history.py\n"
        "?? __pycache__/\n"
        "A  04_testing/pytest/unit/test_canary_dirt_filter.py\n"
    )
    dirty, surviving = compute_dirty(porcelain)
    assert dirty is True
    assert surviving == [
        " M 03_implementation/src/hermes3d/services/code_history.py",
        "A  04_testing/pytest/unit/test_canary_dirt_filter.py",
    ]


def test_empty_porcelain_reports_clean() -> None:
    """An empty porcelain blob means HEAD == working tree -> dirty=False."""
    dirty, surviving = compute_dirty("")
    assert dirty is False
    assert surviving == []


def test_nested_noise_paths_classified() -> None:
    """Nested entries inside a venv / cache classify as noise too.

    git emits forward-slash paths even on Windows, so a deep entry like
    ``.venv-canary/lib/site-packages/foo.py`` MUST also classify as noise.
    The brief's pattern ``\\.venv[-_].*`` is anchored against any path
    segment, not just the basename.
    """
    deep_paths = [
        ".venv-canary/lib/site-packages/foo.py",
        ".venv_unit/Scripts/pip.exe",
        "subdir/__pycache__/module.cpython-311.pyc",
        "package/.pytest_cache/v/cache/lastfailed",
        "build/lib/pkg.egg-info/PKG-INFO",
        ".coverage.host.12345.987654",
    ]
    for path in deep_paths:
        assert is_noise_path(path), f"expected {path!r} to be classified noise"


def test_tracked_files_not_misclassified() -> None:
    """Real source paths must NOT match the noise patterns.

    Defensive coverage: paths that *contain* substrings like ``venv`` but
    aren't venv folders (e.g. ``services/venv_helper.py``) must remain
    classified as real files. The patterns require a separator anchor or
    start-of-string, so a literal ``venv`` substring inside a filename
    does not falsely match.
    """
    real_paths = [
        "03_implementation/src/hermes3d/services/code_history.py",
        "03_implementation/src/hermes3d/api/routes/agent_updates.py",
        "04_testing/pytest/unit/test_canary_dirt_filter.py",
        "docs/handoffs/some_venv_helper.md",  # literal substring, not a venv
        "src/conventional_module.py",
    ]
    for path in real_paths:
        assert not is_noise_path(path), f"unexpected noise classification on {path!r}"


def test_rename_porcelain_classified_by_destination() -> None:
    """``XY orig -> dest`` rename lines classify by destination path.

    git status uses ``orig -> dest`` for renames. The filter must inspect
    the destination only — that's the path Git is reporting as the new
    state of the working tree (per git-status man page short-format).
    """
    porcelain = (
        "R  04_testing/pytest/unit/old_name.py -> .venv-canary/lib/foo.py\n"
        "R  04_testing/pytest/unit/old_name.py -> 04_testing/pytest/unit/new_name.py\n"
    )
    surviving = filter_noise_lines(porcelain)
    # First rename targets a venv path -> filtered. Second is a real rename
    # within the test tree -> survives.
    assert len(surviving) == 1
    assert surviving[0].endswith("-> 04_testing/pytest/unit/new_name.py")


def test_windows_backslash_paths_normalised() -> None:
    """Backslash paths (``.venv-canary\\Scripts\\python.exe``) classified.

    git status --porcelain emits forward slashes by spec, but the helper
    is called from other code paths that may pass OS-native paths. Defend
    by normalising backslashes to forward slashes before regex matching.
    """
    assert is_noise_path(".venv-canary\\Scripts\\python.exe")
    assert is_noise_path("subdir\\__pycache__\\foo.pyc")


def test_filter_path_list_preserves_order_and_drops_noise() -> None:
    """``filter_path_list`` returns surviving paths in input order.

    Used by ``code_history.py::repo_status`` after porcelain prefix
    stripping. Must be order-preserving and never mutate the input.
    """
    paths = [
        ".venv-canary/lib/x.py",
        "src/real_file.py",
        "_pip_install.log",
        "tests/another.py",
        ".coverage",
    ]
    survivors = filter_path_list(paths)
    assert survivors == ["src/real_file.py", "tests/another.py"]
    # Ensure caller list is not mutated.
    assert paths[0] == ".venv-canary/lib/x.py"


def test_noise_patterns_compiled_and_nonempty() -> None:
    """Module-level constant invariant: patterns compile and are >=8.

    Detects accidental constant deletion or re-export break.
    """
    assert len(NOISE_PATTERNS) >= 8
    for rx in NOISE_PATTERNS:
        # A compiled re.Pattern exposes ``pattern`` as a non-empty string.
        assert rx.pattern
        assert hasattr(rx, "search")


@pytest.mark.parametrize(
    "porcelain,expected_dirty",
    [
        ("?? .venv/\n", False),
        ("?? .venv-canary/\n", False),
        ("?? venv-canary/\n", False),  # operator forgot the leading dot
        ("?? .pytest_cache/\n", False),
        ("?? .mypy_cache/\n", False),
        ("?? .ruff_cache/\n", False),
        ("?? .coverage\n", False),
        ("?? .coverage.host.12345.987654\n", False),
        ("?? pkg.egg-info/PKG-INFO\n", False),
        ("?? .tox/py311/bin/python\n", False),
        ("?? real_change.py\n", True),
        (" M tracked.py\n", True),
    ],
)
def test_compute_dirty_matrix(porcelain: str, expected_dirty: bool) -> None:
    """Parametrised matrix: each documented noise category returns clean."""
    dirty, _surviving = compute_dirty(porcelain)
    assert dirty is expected_dirty, f"compute_dirty({porcelain!r}) -> {dirty}"
