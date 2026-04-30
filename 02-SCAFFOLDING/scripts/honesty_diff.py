#!/usr/bin/env python3
"""
scripts/honesty_diff.py — reconcile HONESTY_LEDGER.md tier annotations
against the actual file inventory in KIT_MANIFEST.json.

Reports drift in three buckets:
  1. Files marked runnable in the manifest but called out as scaffold/spec
     in the ledger (or vice versa)
  2. Files in the manifest that the ledger doesn't mention at all
  3. Modules the ledger names but that don't exist on disk

Usage:
    python scripts/honesty_diff.py
    python scripts/honesty_diff.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LEDGER = REPO_ROOT / "00-CONTRACT" / "HONESTY_LEDGER.md"
MANIFEST = REPO_ROOT / "00-CONTRACT" / "KIT_MANIFEST.json"


def load_manifest() -> dict:
    if not MANIFEST.exists():
        print(f"[FAIL] manifest not found at {MANIFEST}")
        print("       run: python 00-CONTRACT/_generate_manifest.py")
        sys.exit(2)
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def load_ledger() -> dict[str, str]:
    """Parse the HONESTY_LEDGER.md and extract path -> tier mappings.

    The ledger names files in code spans, e.g. ``core.farm.print_history``
    or ``02-SCAFFOLDING/src/hermes3d/core/farm/backup.py``. We harvest
    every distinct path-like token and try to bucket it by the nearest
    section heading (## Runnable / ## Scaffold / ## Spec).
    """
    if not LEDGER.exists():
        return {}
    text = LEDGER.read_text(encoding="utf-8")
    # Walk line by line, tracking current section
    bucket = "unknown"
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"##+\s*(.+)", line)
        if m:
            heading = m.group(1).strip().lower()
            if "runnable" in heading or "tier 1" in heading:
                bucket = "runnable"
            elif "scaffold" in heading or "tier 2" in heading:
                bucket = "scaffold"
            elif "spec" in heading or "tier 3" in heading:
                bucket = "spec"
            else:
                bucket = heading
            continue
        # Code spans: `core.foo.bar` or `path/to/file.py`
        for tok in re.findall(r"`([A-Za-z0-9_./\-]+)`", line):
            if (
                "/" in tok or
                tok.endswith(".py") or
                tok.startswith("core.") or
                tok.startswith("api.") or
                tok.startswith("app.") or
                tok.startswith("cli.")
            ):
                out[tok] = bucket
    return out


def normalise_module(tok: str) -> str:
    """Normalise a ledger token into a manifest-style path."""
    tok = tok.strip()
    # core/foo/bar.py form
    if tok.startswith(("core/", "api/", "app/", "cli/")) and tok.endswith(".py"):
        return f"02-SCAFFOLDING/src/hermes3d/{tok}"
    # core.foo.bar form (dotted module)
    if tok.startswith(("core.", "api.", "app.", "cli.")):
        return f"02-SCAFFOLDING/src/hermes3d/{tok.replace('.', '/')}.py"
    if tok.endswith(".py"):
        return tok
    return tok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    ledger = load_ledger()

    by_path = {f["path"]: f for f in manifest["files"]}

    drift: list[dict] = []
    missing_on_disk: list[str] = []

    # Ledger says X is tier T; manifest disagrees
    for tok, ledger_tier in ledger.items():
        norm = normalise_module(tok)
        info = by_path.get(norm)
        if info is None:
            # ledger may name a generic concept rather than a file; skip
            if norm.endswith(".py"):
                missing_on_disk.append(norm)
            continue
        if ledger_tier in {"runnable", "scaffold", "spec"} and info["tier"] != ledger_tier:
            drift.append({
                "path": info["path"],
                "ledger_tier": ledger_tier,
                "manifest_tier": info["tier"],
            })

    # Manifest has files the ledger doesn't mention (informational only)
    ledger_norms = {normalise_module(t) for t in ledger}
    unmentioned = sorted(
        f["path"] for f in manifest["files"]
        if f["tier"] in {"scaffold", "spec"} and f["path"] not in ledger_norms
    )

    summary = {
        "drift": len(drift),
        "missing_on_disk": len(missing_on_disk),
        "unmentioned_non_runnable": len(unmentioned),
    }

    if args.json:
        print(json.dumps({
            "summary": summary,
            "drift": drift,
            "missing_on_disk": missing_on_disk,
            "unmentioned_non_runnable": unmentioned,
        }, indent=2))
    else:
        print(f"[honesty-diff] {summary}")
        if drift:
            print("[honesty-diff] DRIFT — manifest tier disagrees with ledger:")
            for d in drift:
                print(f"  {d['path']}: ledger={d['ledger_tier']}, manifest={d['manifest_tier']}")
        if missing_on_disk:
            print("[honesty-diff] LEDGER NAMES FILES NOT ON DISK:")
            for p in missing_on_disk:
                print(f"  {p}")
        if unmentioned:
            print(f"[honesty-diff] {len(unmentioned)} non-runnable files unmentioned in ledger (informational):")
            for p in unmentioned[:10]:
                print(f"  {p}")
            if len(unmentioned) > 10:
                print(f"  ...and {len(unmentioned) - 10} more")
        if not drift and not missing_on_disk:
            print("[honesty-diff] no drift detected.")

    return 1 if (drift or missing_on_disk) else 0


if __name__ == "__main__":
    sys.exit(main())
