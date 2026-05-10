#!/usr/bin/env python3
"""Fail when active production UI code exposes fake/mock/simulated UX."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
FORBIDDEN_TERMS = (
    "mock",
    "mocked",
    "fake",
    "faked",
    "simulated",
    "simulation",
    "demo",
    "sample",
    "placeholder",
    "dummy",
    "fixture",
    "lorem",
)
TERM_RE = re.compile(r"\b(" + "|".join(re.escape(term) for term in FORBIDDEN_TERMS) + r")\b", re.IGNORECASE)
IMPORT_RE = re.compile(
    r"""
    (?:\bimport\s+(?:type\s+)?(?:[\s\S]*?\s+from\s+)?|\bexport\s+(?:type\s+)?[\s\S]*?\s+from\s+)
    ["']([^"']+)["']
    |
    \bimport\s*\(\s*["']([^"']+)["']\s*\)
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Finding:
    kind: str
    path: Path
    line: int
    detail: str
    text: str


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def strip_comments(source: str) -> str:
    out: list[str] = []
    i = 0
    state = "code"
    quote = ""
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "code":
            if ch == "/" and nxt == "/":
                out.extend((" ", " "))
                i += 2
                while i < len(source) and source[i] != "\n":
                    out.append(" ")
                    i += 1
                continue
            if ch == "/" and nxt == "*":
                out.extend((" ", " "))
                i += 2
                while i < len(source):
                    if source[i] == "*" and i + 1 < len(source) and source[i + 1] == "/":
                        out.extend((" ", " "))
                        i += 2
                        break
                    out.append("\n" if source[i] == "\n" else " ")
                    i += 1
                continue
            if ch in ("'", '"', "`"):
                state = "string"
                quote = ch
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        if ch == "\\":
            if i + 1 < len(source):
                out.append(source[i + 1])
                i += 2
            else:
                i += 1
            continue
        if ch == quote:
            state = "code"
        i += 1
    return "".join(out)


def iter_string_literals(source_without_comments: str) -> list[tuple[int, str]]:
    strings: list[tuple[int, str]] = []
    i = 0
    line = 1
    while i < len(source_without_comments):
        ch = source_without_comments[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch not in ("'", '"', "`"):
            i += 1
            continue
        quote = ch
        start_line = line
        i += 1
        value: list[str] = []
        while i < len(source_without_comments):
            ch = source_without_comments[i]
            if ch == "\n":
                line += 1
            if ch == "\\":
                if i + 1 < len(source_without_comments):
                    value.append(source_without_comments[i + 1])
                    if source_without_comments[i + 1] == "\n":
                        line += 1
                    i += 2
                    continue
                i += 1
                continue
            if ch == quote:
                i += 1
                break
            value.append(ch)
            i += 1
        strings.append((start_line, "".join(value)))
    return strings


def line_text(source: str, line: int) -> str:
    lines = source.splitlines()
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return ""


def resolve_import(importer: Path, specifier: str, ui_src: Path) -> Path | None:
    if not specifier.startswith("."):
        return None
    base = (importer.parent / specifier).resolve()
    candidates: list[Path] = []
    if base.suffix:
        candidates.append(base)
    else:
        candidates.extend(base.with_suffix(ext) for ext in EXTENSIONS)
        candidates.extend(base / f"index{ext}" for ext in EXTENSIONS)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.resolve().is_relative_to(ui_src):
            return candidate.resolve()
    return None


def imports_from(path: Path) -> tuple[str, list[str]]:
    source = path.read_text(encoding="utf-8")
    cleaned = strip_comments(source)
    imports = [match.group(1) or match.group(2) for match in IMPORT_RE.finditer(cleaned)]
    return source, imports


def discover_active_files(entry: Path, ui_src: Path) -> tuple[set[Path], list[Finding]]:
    seen: set[Path] = set()
    stack = [entry.resolve()]
    findings: list[Finding] = []
    while stack:
        path = stack.pop()
        if path in seen or path.parts[-2:] == ("data", "mock"):
            continue
        seen.add(path)
        source, imports = imports_from(path)
        for specifier in imports:
            normalized = specifier.replace("\\", "/")
            if "data/mock" in normalized:
                line = source[: source.find(specifier)].count("\n") + 1 if specifier in source else 1
                findings.append(
                    Finding(
                        kind="mock-data-import",
                        path=path,
                        line=line,
                        detail=f'import from "{specifier}"',
                        text=line_text(source, line),
                    )
                )
                continue
            resolved = resolve_import(path, specifier, ui_src)
            if resolved is not None:
                stack.append(resolved)
    return seen, findings


def scan_strings(paths: set[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(paths):
        source = path.read_text(encoding="utf-8")
        cleaned = strip_comments(source)
        for line, value in iter_string_literals(cleaned):
            raw_line = line_text(source, line)
            stripped = raw_line.lstrip()
            if stripped.startswith(("import ", "export ")) or " import(" in raw_line:
                continue
            match = TERM_RE.search(value)
            if match:
                findings.append(
                    Finding(
                        kind="forbidden-visible-term",
                        path=path,
                        line=line,
                        detail=f'term "{match.group(1)}" in string/template literal',
                        text=raw_line,
                    )
                )
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root_from_script())
    parser.add_argument("--json", action="store_true", help="Emit machine-readable findings.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    ui_src = repo_root / "03_implementation" / "ui" / "src"
    entry = ui_src / "App.tsx"
    if not entry.exists():
        print(f"Missing active UI entry: {entry}", file=sys.stderr)
        return 2

    active_files, import_findings = discover_active_files(entry, ui_src)
    findings = [*import_findings, *scan_strings(active_files)]

    payload = {
        "entry": str(entry),
        "active_file_count": len(active_files),
        "forbidden_terms": FORBIDDEN_TERMS,
        "finding_count": len(findings),
        "findings": [
            {
                "kind": finding.kind,
                "path": str(finding.path.relative_to(repo_root)),
                "line": finding.line,
                "detail": finding.detail,
                "text": finding.text,
            }
            for finding in findings
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Active UI no-fake scan: {len(active_files)} production files from {entry.relative_to(repo_root)}")
        if findings:
            for finding in findings:
                rel = finding.path.relative_to(repo_root)
                print(f"{rel}:{finding.line}: {finding.kind}: {finding.detail}")
                print(f"  {finding.text}")
        else:
            print("No production mock/fake/simulated UX markers found.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
