"""Filter pip / pytest / venv noise out of ``git status --porcelain`` output.

Wave 1 promotion left a v0.13 canary checkout at
``G:/Github/hermes-agent-v013-canary`` whose first ``pip install -e .`` produced
``.venv-canary/`` and ``_pip_install.log`` as untracked entries. ``git status
--porcelain`` correctly reports both as ``??``, so any reader that flips
``dirty=True`` whenever the porcelain output is non-empty (``_repo_state`` in
``api/routes/agent_updates.py`` and ``repo_status`` in ``services/code_history.py``)
flagged the canary as outdated/dirty even though the working tree was identical
to the ``v2026.5.7`` tag at HEAD.

The fix lives in **Hermes3D's update-status checker**, not the upstream repo
(brief: do NOT modify the canary checkout itself). This module ignores
filesystem artifacts that pip / pytest / coverage / setuptools generate
*outside* version control, so the dirty signal only fires when the operator
has actually edited tracked files.

References
----------
- ``git status --porcelain`` line format and codes ``??`` / `` M`` / ``M `` /
  ``A `` / ``D ``: https://git-scm.com/docs/git-status#_short_format
- ``pathlib.PurePath.match`` glob semantics for the noise classifier:
  https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.match

Public surface
--------------
- :data:`NOISE_PATTERNS` — frozen tuple of regex patterns matched against the
  stripped path token of each porcelain line.
- :func:`is_noise_path` — single-path predicate.
- :func:`filter_noise_lines` — drop noise lines from a porcelain blob.
- :func:`compute_dirty` — high-level "is the tree actually dirty?" verdict
  used by callers that need just a bool plus the surviving entries.
"""

from __future__ import annotations

import re
from typing import Iterable

# Patterns are anchored against the *path token* of each ``git status
# --porcelain`` line (everything after the two-char status + single space).
# Each pattern matches the basename or any path segment, so nested entries
# such as ``.venv-canary/lib/site-packages/foo.py`` also classify as noise.
#
# Order is informational only — :func:`is_noise_path` short-circuits on first
# match. Patterns are case-insensitive on Windows path comparisons because
# ``git status`` emits forward-slash paths but the underlying filesystem on
# Windows is case-insensitive (the canary path lives on NTFS).
_NOISE_REGEXES: tuple[str, ...] = (
    # Virtual environments — `.venv-canary/`, `.venv_unit/`, `venv/` (any
    # leading or embedded segment). The leading-dot prefix is optional
    # because some operators name their venv ``venv-canary`` without the dot.
    r"(^|/)\.?venv[-_].*",
    r"(^|/)\.?venv($|/)",
    # Pip artifacts left by ``pip install -e .`` and friends.
    r"(^|/)_pip_install\.log$",
    r"(^|/)pip-(?:wheel|build|log)-.+",
    # Bytecode / compiler caches.
    r"(^|/)__pycache__($|/)",
    # pytest, mypy, ruff caches.
    r"(^|/)\.pytest_cache($|/)",
    r"(^|/)\.mypy_cache($|/)",
    r"(^|/)\.ruff_cache($|/)",
    # Coverage data files (``coverage run`` writes ``.coverage`` and
    # ``.coverage.<host>.<pid>.<rand>``).
    r"(^|/)\.coverage(\..+)?$",
    # Setuptools metadata produced by editable installs.
    r"(^|/).+\.egg-info($|/)",
    # tox / nox managed environments.
    r"(^|/)\.tox($|/)",
    r"(^|/)\.nox($|/)",
)

NOISE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pat, re.IGNORECASE) for pat in _NOISE_REGEXES
)


def _strip_porcelain_prefix(line: str) -> str:
    """Return the path token from a ``git status --porcelain=v1`` line.

    Porcelain v1 layout (per ``git status --porcelain`` man page):

        XY <path>

    where ``XY`` is the two-char status code and is always followed by a
    single space, then the path. Renames use ``XY <orig> -> <new>`` — the
    original path is discarded and only the destination classified, which
    matches Git's own ``status`` view.
    """
    if not line:
        return ""
    # Lines shorter than the 3-char prefix can't be valid porcelain output.
    if len(line) < 4:
        return line.strip()
    # Skip the two-char status + one space. The man page guarantees this
    # prefix is exactly 3 bytes wide for porcelain v1.
    body = line[3:]
    if " -> " in body:
        # Rename / copy: ``orig -> dest``; classify by destination only.
        body = body.split(" -> ", 1)[1]
    # Quoted paths (``\"path with spaces\"``) preserve their quoting; strip
    # only the surrounding quotes since the regexes are anchored against
    # path segments and don't care about embedded spaces.
    body = body.strip()
    if len(body) >= 2 and body.startswith('"') and body.endswith('"'):
        body = body[1:-1]
    return body


def is_noise_path(path: str) -> bool:
    """Return ``True`` if *path* is a pip/pytest/venv artifact.

    The check is path-token aware (uses regex anchors against ``/`` or the
    start of the string) and case-insensitive so Windows entries match the
    same patterns as POSIX ones.
    """
    if not path:
        return False
    # ``git status`` always emits forward slashes regardless of platform;
    # callers that pass OS-native paths get normalised here defensively.
    normalised = path.replace("\\", "/").strip().rstrip("/")
    if not normalised:
        return False
    return any(rx.search(normalised) for rx in NOISE_PATTERNS)


def filter_noise_lines(porcelain_text: str) -> list[str]:
    """Return non-noise porcelain lines from a ``git status --porcelain`` blob.

    Empty input (no untracked or modified files) returns ``[]`` immediately.
    Each surviving line is stripped of trailing whitespace but otherwise
    preserved verbatim so callers can render the original status codes.
    """
    if not porcelain_text:
        return []
    surviving: list[str] = []
    for raw_line in porcelain_text.splitlines():
        if not raw_line.strip():
            continue
        path = _strip_porcelain_prefix(raw_line)
        if is_noise_path(path):
            continue
        surviving.append(raw_line.rstrip())
    return surviving


def compute_dirty(porcelain_text: str) -> tuple[bool, list[str]]:
    """High-level dirty verdict + filtered porcelain lines.

    Returns ``(dirty, surviving_lines)`` where:

    - ``dirty`` is ``True`` only if at least one porcelain line refers to a
      file that is **not** classified as noise. A canary checkout that has
      *only* ``.venv-canary/`` and ``_pip_install.log`` therefore reports
      ``dirty=False``.
    - ``surviving_lines`` is the filtered porcelain output suitable for
      logging back to the operator. Empty when nothing survives or when
      ``porcelain_text`` was empty.

    Callers that only need the bool can ignore the second element.
    """
    surviving = filter_noise_lines(porcelain_text)
    return bool(surviving), surviving


def filter_path_list(paths: Iterable[str]) -> list[str]:
    """Drop noise paths from an arbitrary iterable of bare path strings.

    Used by ``services/code_history.py::repo_status`` after it has already
    stripped the porcelain prefix into a list of changed files. Returns a
    new list preserving input order; never mutates the iterable.
    """
    return [p for p in paths if not is_noise_path(p)]


__all__ = [
    "NOISE_PATTERNS",
    "is_noise_path",
    "filter_noise_lines",
    "compute_dirty",
    "filter_path_list",
]
