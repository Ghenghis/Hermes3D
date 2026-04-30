#!/usr/bin/env python3
"""Validate every agents/*.yaml manifest against agents/_schema.json.

Exit 0 if all manifests validate, 1 otherwise. On success prints one
green ``[OK] <role>`` line per manifest.

Usage:
    python scripts/validate-agents.py [--agents-dir DIR]

Dependencies: pyyaml, jsonschema (already pinned in requirements-dev.txt).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("error: pyyaml is required (pip install -r requirements-dev.txt)",
          file=sys.stderr)
    sys.exit(2)

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    print("error: jsonschema is required (pip install -r requirements-dev.txt)",
          file=sys.stderr)
    sys.exit(2)


GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def _color(s: str, code: str) -> str:
    if not sys.stdout.isatty():
        return s
    return f"{code}{s}{RESET}"


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents-dir", type=Path,
                        default=repo_root / "agents",
                        help="Directory containing _schema.json and *.yaml manifests.")
    args = parser.parse_args(argv)

    schema_path = args.agents_dir / "_schema.json"
    if not schema_path.is_file():
        print(f"error: schema not found at {schema_path}", file=sys.stderr)
        return 1

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    manifests = sorted(p for p in args.agents_dir.glob("*.yaml")
                        if not p.name.startswith("_"))
    if not manifests:
        print(f"error: no manifests found in {args.agents_dir}", file=sys.stderr)
        return 1

    failures: list[tuple[Path, list[str]]] = []
    for path in manifests:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            failures.append((path, [f"yaml parse error: {e}"]))
            continue

        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        role = (data or {}).get("role", path.stem) if isinstance(data, dict) else path.stem

        # Extra check: filename stem must match role field.
        if isinstance(data, dict) and data.get("role") and data["role"] != path.stem:
            errors.append(_synth_error(
                f"role field '{data['role']}' must match filename stem '{path.stem}'"))

        if errors:
            failures.append((path, [_format_error(e) for e in errors]))
        else:
            print(f"{_color('[OK]', GREEN)} {role}  ({path.relative_to(repo_root)})")

    if failures:
        print()
        for path, errs in failures:
            print(f"{_color('[FAIL]', RED)} {path}")
            for err in errs:
                print(f"   - {err}")
        print()
        print(f"{len(failures)} of {len(manifests)} manifest(s) invalid.",
              file=sys.stderr)
        return 1

    print()
    print(f"All {len(manifests)} manifest(s) valid.")
    return 0


class _SynthError:
    def __init__(self, message: str) -> None:
        self.message = message
        self.path: list[str] = []


def _synth_error(message: str) -> _SynthError:
    return _SynthError(message)


def _format_error(err: object) -> str:
    msg = getattr(err, "message", str(err))
    path = list(getattr(err, "path", []) or [])
    if path:
        return f"{'.'.join(str(p) for p in path)}: {msg}"
    return msg


if __name__ == "__main__":
    sys.exit(main())
