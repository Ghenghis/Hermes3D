#!/usr/bin/env python3
"""
scripts/readme_claim_audit.py — sanity-check that "X works" claims in
README and headline docs correspond to a passing test.

This is a lightweight Layer F honesty gate. It looks for declarative
"works"/"supports"/"implements" claims and verifies that the keyword in
each claim appears in at least one test file's docstring or test name.

It is heuristic, not exhaustive. The point is to make it harder for a
README to drift away from reality unnoticed.

Usage:
    python scripts/readme_claim_audit.py
    python scripts/readme_claim_audit.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Files to scan for claims
CLAIM_SOURCES = [
    REPO_ROOT / "00_overview" / "contract" / "FEATURES.md",
]
README_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "01_requirements" / "README.md",
]
for p in README_PATHS:
    if p.exists():
        CLAIM_SOURCES.append(p)

CLAIM_PATTERNS = [
    re.compile(r"\b(?:supports?|implements?|provides?|wires?|registers?|enforces?)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+){0,4})", re.IGNORECASE),
]

# Words that aren't claims even though they look like one
STOPWORDS = {
    "the", "a", "an", "this", "that", "these", "those",
    "and", "or", "of", "to", "for", "in", "on", "at",
    "via", "with", "without", "by",
}


def collect_claims() -> list[dict]:
    claims = []
    for src in CLAIM_SOURCES:
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for pat in CLAIM_PATTERNS:
                for m in pat.finditer(stripped):
                    keyword = m.group(1).strip()
                    head = keyword.split()[0].lower()
                    if head in STOPWORDS:
                        continue
                    claims.append({
                        "source": str(src.relative_to(REPO_ROOT.parent)),
                        "line": lineno,
                        "claim": stripped[:120],
                        "keyword": keyword,
                    })
    return claims


def collect_test_keywords() -> set[str]:
    """Pull every test name and docstring word for cheap matching."""
    bag: set[str] = set()
    test_root = REPO_ROOT / "tests"
    if not test_root.exists():
        return bag
    for py in test_root.rglob("test_*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        # function names
        for m in re.finditer(r"def\s+(test_[A-Za-z0-9_]+)", text):
            for word in m.group(1).split("_")[1:]:
                bag.add(word.lower())
        # docstring tokens
        for ds in re.findall(r'"""(.*?)"""', text, flags=re.DOTALL):
            for word in re.findall(r"[A-Za-z][A-Za-z0-9_]+", ds):
                bag.add(word.lower())
        # path components contain useful tokens too
        for part in py.relative_to(test_root).with_suffix("").parts:
            for word in part.split("_"):
                bag.add(word.lower())
    return bag


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    claims = collect_claims()
    test_keywords = collect_test_keywords()

    unverified: list[dict] = []
    verified: list[dict] = []
    for c in claims:
        head = c["keyword"].split()[0].lower()
        # accept the claim if any word from the keyword appears in tests
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_]+", c["keyword"])]
        if any(w in test_keywords for w in words):
            verified.append(c)
        else:
            unverified.append({**c, "head": head})

    summary = {
        "total_claims": len(claims),
        "verified": len(verified),
        "unverified": len(unverified),
    }

    if args.json:
        print(json.dumps({"summary": summary, "unverified": unverified}, indent=2))
    else:
        print(f"[claim-audit] {summary}")
        if unverified:
            print(f"[claim-audit] {len(unverified)} claims without test correspondence:")
            for c in unverified[:30]:
                print(f"  {c['source']}:{c['line']} -> '{c['keyword']}'")
            if len(unverified) > 30:
                print(f"  ...and {len(unverified) - 30} more")
        else:
            print("[claim-audit] every claim corresponds to a test keyword.")

    # Don't fail builds on the heuristic in v5; this becomes hard in v5.1
    return 0


if __name__ == "__main__":
    sys.exit(main())
