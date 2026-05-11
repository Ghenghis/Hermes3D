"""Hermes3D env-file loader.

Hydrates :data:`os.environ` from operator-managed ``.env`` files BEFORE the
FastAPI app instantiates routes that read env at import-time. Required so
the backend can pick up ``MINIMAX_API_KEY``, ``DEEPSEEK_API_KEY``, and other
credentials kept out of the repo under ``G:\\private\\.env`` (the operator's
secret-storage convention from the 2026-05-03 .env.txt screenshot incident).

Contract:
  * Existing entries in ``os.environ`` are NEVER overwritten — the explicit
    CI / shell environment always wins over the file. (``override=False``.)
  * Missing files are not errors — the loader simply logs which files were
    found and which were skipped.
  * KEY NAMES are logged at INFO; VALUES are NEVER logged. The function is
    safe to call in production with secret-rich files.
  * Honors ``HERMES3D_ENV_FILES`` (semicolon-separated list); falls back to
    ``DEFAULT_ENV_FILES`` if unset.

Usage:
    from hermes3d.config.env_loader import load_at_startup
    load_at_startup()    # call FIRST in app factory, before route imports
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

LOG = logging.getLogger(__name__)


# Default lookup order. The operator's secret-storage convention places the
# real keys at G:\private\.env. The local repo .env (if any) is consulted
# second so a developer can override per-checkout without touching G:\private\.
DEFAULT_ENV_FILES: tuple[str, ...] = (
    r"G:\private\.env",
    ".env",
)


def _candidate_files() -> list[Path]:
    """Resolve the candidate .env files in priority order.

    ``HERMES3D_ENV_FILES`` overrides the default list when set. Entries are
    semicolon-separated, leading/trailing whitespace stripped. Empty entries
    are dropped.
    """
    raw = os.environ.get("HERMES3D_ENV_FILES", "")
    if raw.strip():
        items = [chunk.strip() for chunk in raw.split(";") if chunk.strip()]
    else:
        items = list(DEFAULT_ENV_FILES)
    return [Path(item) for item in items]


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict.

    Recognises ``KEY=value`` lines. Supports quoted values (``"..."`` or
    ``'...'``). Trims inline ``#`` comments only when they follow whitespace
    AND the value is not quoted. Ignores blank lines and full-line comments
    starting with ``#``.

    The parser is deliberately conservative — we prefer to skip a malformed
    line than to mis-parse a secret and leak it into the wrong key.
    """
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        LOG.debug("env_loader: %s unreadable (%s) — skipping", path, exc)
        return out
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            LOG.debug("env_loader: %s:%d malformed (no '='), skipping", path, line_no)
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes (single or double).
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif " #" in value:
            # Inline comment after whitespace (only when value not quoted).
            value = value.split(" #", 1)[0].rstrip()
        if not key or not key.replace("_", "").isalnum():
            LOG.debug("env_loader: %s:%d non-identifier key %r — skipping", path, line_no, key)
            continue
        out[key] = value
    return out


def load_at_startup(
    candidates: list[Path] | None = None,
    *,
    override: bool = False,
) -> dict[str, list[str]]:
    """Hydrate ``os.environ`` from each candidate .env file in order.

    Args:
        candidates: explicit list of paths (mainly for tests). When ``None``,
            uses :func:`_candidate_files` which honors ``HERMES3D_ENV_FILES``.
        override: when ``True``, existing env entries are replaced. Default
            ``False`` (explicit env always wins, per the contract).

    Returns:
        A report dict::

            {
              "applied":      ["MINIMAX_API_KEY", "DEEPSEEK_API_KEY", ...],
              "skipped_set":  ["HOME", ...],   # already set in os.environ
              "skipped_invalid": [],            # malformed lines / keys
              "files_found": ["G:\\private\\.env"],
              "files_missing": [".env"],
            }

        KEYS are logged; VALUES are never returned or logged.
    """
    cands = candidates if candidates is not None else _candidate_files()
    report: dict[str, list[str]] = {
        "applied": [],
        "skipped_set": [],
        "skipped_invalid": [],
        "files_found": [],
        "files_missing": [],
    }
    for path in cands:
        if not path.is_file():
            report["files_missing"].append(str(path))
            LOG.debug("env_loader: %s missing — skipping", path)
            continue
        report["files_found"].append(str(path))
        try:
            parsed = _parse_env_file(path)
        except Exception as exc:  # pragma: no cover - defensive
            LOG.warning("env_loader: failed to parse %s: %s", path, exc)
            continue
        for key, value in parsed.items():
            if key in os.environ and not override:
                report["skipped_set"].append(key)
                continue
            os.environ[key] = value
            report["applied"].append(key)
    LOG.info(
        "env_loader: applied=%d skipped_set=%d files_found=%d files_missing=%d",
        len(report["applied"]),
        len(report["skipped_set"]),
        len(report["files_found"]),
        len(report["files_missing"]),
    )
    if report["applied"]:
        # Key NAMES only — never values.
        LOG.info("env_loader: applied keys: %s", ", ".join(sorted(report["applied"])))
    return report


__all__ = ["DEFAULT_ENV_FILES", "load_at_startup"]
