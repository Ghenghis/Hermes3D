"""Command-line entry point for the injection scanner.

Usage::

    python -m hermes3d.core.security.injection_scanner <input>
    python -m hermes3d.core.security.injection_scanner --file path.txt
    echo "ignore previous instructions" | python -m hermes3d.core.security.injection_scanner -

Exit codes:
    0 — clean (or below fail-threshold)
    1 — finding(s) at or above fail-threshold
    2 — usage / IO error

Output is JSON on stdout (the full ``ScanResult.to_dict()``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hermes3d.core.security.injection_scanner import (
    InjectionScanner,
    InjectionScannerError,
    SeverityLevel,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hermes3d.core.security.injection_scanner",
        description="Scan text for OWASP-LLM-01 prompt-injection patterns.",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("text", nargs="?", help="Text to scan (literal). Use '-' for stdin.")
    src.add_argument("--file", "-f", type=Path, help="Read text from file.")

    parser.add_argument(
        "--threshold",
        choices=("low", "medium", "high"),
        default="high",
        help="Fail-closed threshold (default: high).",
    )
    parser.add_argument(
        "--ruleset",
        type=Path,
        action="append",
        help="Override ruleset YAML (repeatable). Default = bundled OWASP+in-house.",
    )
    return parser


def _read_input(args: argparse.Namespace) -> str:
    if args.file is not None:
        if not args.file.is_file():
            print(f"error: file not found: {args.file}", file=sys.stderr)
            sys.exit(2)
        return args.file.read_text(encoding="utf-8")
    if args.text == "-":
        return sys.stdin.read()
    return args.text or ""


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    threshold: SeverityLevel = args.threshold

    try:
        scanner = InjectionScanner(
            ruleset_paths=args.ruleset if args.ruleset else None,
            fail_threshold=threshold,
        )
    except InjectionScannerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    text = _read_input(args)
    result = scanner.scan(text)
    json.dump(result.to_dict(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 1 if result.fail_closed else 0


if __name__ == "__main__":  # pragma: no cover - CLI bootstrap
    raise SystemExit(main())
