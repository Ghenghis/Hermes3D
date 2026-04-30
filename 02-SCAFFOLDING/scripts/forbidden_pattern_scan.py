#!/usr/bin/env python3
"""
scripts/forbidden_pattern_scan — flag stub markers in runtime code.

Scans every .py file under src/hermes3d for forbidden patterns and reports
them. Exits 1 if any are found.

Forbidden patterns (any case):
  - TODO / FIXME / STUB / PLACEHOLDER / NOT_IMPLEMENTED
  - `raise NotImplementedError(...)` outside abstract base classes
  - `except: pass` bare empty handlers

Usage:
    python scripts/forbidden_pattern_scan
    python scripts/forbidden_pattern_scan --json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "hermes3d"

PATTERNS = re.compile(
    r"\b(TODO|FIXME|STUB|PLACEHOLDER|NOT_IMPLEMENTED)\b", re.IGNORECASE
)


def scan_file_text(path: Path) -> list[dict]:
    """Find forbidden text patterns line-by-line."""
    hits = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Strip out string literals and docstring blocks where the marker
        # might appear in a "this would be a TODO if we implemented it"
        # contract section.
        if "noqa: forbidden_pattern_scan" in line:
            continue
        m = PATTERNS.search(line)
        if m:
            hits.append({
                "path": str(path.relative_to(REPO_ROOT)),
                "line": lineno,
                "rule": "text_pattern",
                "match": m.group(0),
                "snippet": line.strip()[:120],
            })
    return hits


def scan_file_ast(path: Path) -> list[dict]:
    """Find structural forbidden patterns via AST."""
    hits = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [{
            "path": str(path.relative_to(REPO_ROOT)),
            "line": exc.lineno or 0,
            "rule": "syntax_error",
            "match": "",
            "snippet": str(exc),
        }]

    def has_noqa(line_no: int) -> bool:
        # Honor noqa on this line OR the line above (for multi-line raises).
        for ln in (line_no, line_no - 1):
            if 1 <= ln <= len(lines) and "noqa: forbidden_pattern_scan" in lines[ln - 1]:
                return True
        return False

    # bare except: pass
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if (
                node.type is None
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Pass)
                and not has_noqa(node.lineno)
            ):
                hits.append({
                    "path": str(path.relative_to(REPO_ROOT)),
                    "line": node.lineno,
                    "rule": "bare_except_pass",
                    "match": "except: pass",
                    "snippet": "",
                })
        # raise NotImplementedError outside abstract methods
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            f = node.exc.func
            name = (
                f.id if isinstance(f, ast.Name)
                else getattr(f, "attr", None)
            )
            if name == "NotImplementedError" and not has_noqa(node.lineno):
                hits.append({
                    "path": str(path.relative_to(REPO_ROOT)),
                    "line": node.lineno,
                    "rule": "raise_not_implemented",
                    "match": "raise NotImplementedError",
                    "snippet": "",
                })
    return hits


def is_abstract_method_raise(path: Path, lineno: int) -> bool:
    """Best-effort: skip raises in methods immediately preceded by
    ``@abstractmethod`` or in classes inheriting from ``ABC``."""
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and any(
            isinstance(d, ast.Name) and d.id == "abstractmethod"
            for d in node.decorator_list
        ):
            # check the raise is inside this function
            end = getattr(node, "end_lineno", node.lineno + 50)
            if node.lineno <= lineno <= end:
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", default=str(SRC))
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"[FAIL] root not found: {root}")
        return 1

    all_hits: list[dict] = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        hits = scan_file_text(path) + scan_file_ast(path)
        # Filter out abstract-method NotImplementedError raises
        hits = [
            h for h in hits
            if not (
                h["rule"] == "raise_not_implemented"
                and is_abstract_method_raise(path, h["line"])
            )
        ]
        all_hits.extend(hits)

    if args.json:
        print(json.dumps({"hits": all_hits, "count": len(all_hits)}, indent=2))
    else:
        if all_hits:
            print(f"[FAIL] {len(all_hits)} forbidden-pattern hit(s):")
            for h in all_hits:
                print(f"  {h['path']}:{h['line']} [{h['rule']}] {h['match']}")
                if h.get("snippet"):
                    print(f"    {h['snippet']}")
        else:
            print("[OK] no forbidden patterns found.")

    return 1 if all_hits else 0


if __name__ == "__main__":
    sys.exit(main())
