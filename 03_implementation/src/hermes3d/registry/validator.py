"""Hermes3D registry validator — production implementation.

CLI:
    python -m hermes3d.registry.validator [PATH] [--json]

Returns exit 0 on PASS, 1 on FAIL. Output is human-readable text by default,
JSON with --json (for CI consumption).

Tasks 6-8 add URL shape, per-type capability matrix, and tested_versions
rules incrementally — Task 5 ships only license + structural checks + the
CLI shell so all later tasks can extend `_check_entry()` without re-plumbing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .capability_matrix import is_known_type, required_capabilities_for_type
from .errors import ErrorCode, ValidationError
from .loader import LoaderError, load_registry
from .types import ToolEntry

_INVALID_LICENSE_VALUES = frozenset(
    {"", "unknown", "tbd", "todo", "n/a", "none"},
)

# Generous URL shape: scheme + host + any RFC 3986 reserved/unreserved chars.
# Closes Phase 0 finding LOW-7 (typo'd repo: "https//github.com/x/y" silently
# passed). Empty strings also flagged via reference_url() returning falsy.
_URL_SHAPE = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    checked: int
    errors: tuple[ValidationError, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "errors": [e.to_dict() for e in self.errors],
        }


def _check_license(entry: ToolEntry) -> list[ValidationError]:
    if not entry.license:
        return [
            ValidationError(
                entry.key,
                ErrorCode.MISSING_LICENSE,
                "missing required field 'license'",
            )
        ]
    if entry.license.strip().lower() in _INVALID_LICENSE_VALUES:
        return [
            ValidationError(
                entry.key,
                ErrorCode.INVALID_LICENSE,
                f"license value '{entry.license}' is not a real SPDX id",
            )
        ]
    return []


def _check_capabilities(entry: ToolEntry) -> list[ValidationError]:
    out: list[ValidationError] = []
    if not entry.adapter.capabilities:
        out.append(
            ValidationError(
                entry.key,
                ErrorCode.EMPTY_CAPABILITIES,
                "adapter.capabilities must be non-empty",
            )
        )
    if not is_known_type(entry.type):
        out.append(
            ValidationError(
                entry.key,
                ErrorCode.UNKNOWN_TYPE,
                f"unknown type '{entry.type}'",
                "warning",
            )
        )
    return out


def _check_url(entry: ToolEntry) -> list[ValidationError]:
    """Distinguish 'no URL field declared' (MISSING) from 'declared but malformed'
    (INVALID_URL_SHAPE). Empty-string `repo: ""` is a declaration with bad data,
    not a missing declaration."""
    declared = (entry.repo, entry.source, entry.homepage)
    any_declared = any(v is not None for v in declared)
    if not any_declared:
        return [
            ValidationError(
                entry.key,
                ErrorCode.MISSING_REQUIRED_FIELD,
                "must include a repo, source, or homepage URL",
            )
        ]
    url = entry.reference_url()
    if not isinstance(url, str) or not url.strip() or not _URL_SHAPE.match(url):
        return [
            ValidationError(
                entry.key,
                ErrorCode.INVALID_URL_SHAPE,
                f"reference URL '{url}' is not a well-formed http(s) URL",
            )
        ]
    return []


def _check_per_type_capabilities(entry: ToolEntry) -> list[ValidationError]:
    """Enforce required capability tokens per `type`.

    A `dock_*` token in `_REQUIRED` is satisfied by any capability starting
    with `dock_` (so `dock_if_supported` and `dock_if_allowed` both work).
    `launch_external` is satisfied by either itself or `fullscreen_external`
    (the web-UI equivalent). Other required tokens must match exactly.
    """
    required = required_capabilities_for_type(entry.type)
    if not required:
        return []
    caps = set(entry.adapter.capabilities)
    out: list[ValidationError] = []
    for req in required:
        if req.startswith("dock_"):
            if not any(c.startswith("dock_") for c in caps):
                out.append(
                    ValidationError(
                        entry.key,
                        ErrorCode.MISSING_DOCK_CAPABILITY,
                        f"type '{entry.type}' requires a dock capability "
                        f"(e.g. {req}); none declared",
                    )
                )
        elif req == "launch_external":
            if "launch_external" not in caps and "fullscreen_external" not in caps:
                out.append(
                    ValidationError(
                        entry.key,
                        ErrorCode.MISSING_EXTERNAL_LAUNCH_CAPABILITY,
                        f"type '{entry.type}' requires 'launch_external' or "
                        f"'fullscreen_external'; none declared",
                    )
                )
        elif req not in caps:
            out.append(
                ValidationError(
                    entry.key,
                    ErrorCode.MISSING_REQUIRED_FIELD,
                    f"type '{entry.type}' requires capability '{req}'",
                )
            )
    return out


def _check_entry(entry: ToolEntry) -> list[ValidationError]:
    """Aggregate all per-entry checks. Task 8 extends this list."""
    errs: list[ValidationError] = []
    errs.extend(_check_license(entry))
    errs.extend(_check_capabilities(entry))
    errs.extend(_check_url(entry))
    errs.extend(_check_per_type_capabilities(entry))
    return errs


def validate(entries: Sequence[ToolEntry]) -> ValidationResult:
    """Run all rules across every entry and return a structured result."""
    all_errors: list[ValidationError] = []
    for entry in entries:
        all_errors.extend(_check_entry(entry))
    blocking = [e for e in all_errors if e.severity == "error"]
    return ValidationResult(
        ok=not blocking,
        checked=len(entries),
        errors=tuple(all_errors),
    )


def _default_registry_path() -> Path:
    """Anchor the default to the kit's config dir, not CWD.

    Closes Phase 0 finding LOW-8 (default-path silently fails from repo root).
    Resolves relative to this file: src/hermes3d/registry/validator.py is at
    parents[4] == repo root, then +/hermes3d_gui_contract_kit_v4.1/config/...
    """
    return (
        Path(__file__).resolve().parents[4]
        / "hermes3d_gui_contract_kit_v4.1"
        / "config"
        / "external_repos_registry.yaml"
    )


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hermes3d.registry.validator")
    p.add_argument("path", nargs="?", type=Path, default=_default_registry_path())
    p.add_argument("--json", action="store_true", help="emit JSON instead of human text")
    args = p.parse_args(argv)
    try:
        entries = load_registry(args.path)
    except LoaderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    result = validate(entries)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    elif result.ok:
        print(f"Registry validation PASS: {result.checked} tools checked")
    else:
        print(
            f"Registry validation FAILED: {result.checked} tools checked, "
            f"{len(result.errors)} issues"
        )
        for err in result.errors:
            print(f"- [{err.severity}] {err.tool_id} {err.code.value}: {err.message}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
