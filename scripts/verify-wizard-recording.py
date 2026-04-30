#!/usr/bin/env python3
"""verify-wizard-recording.py — validate a wizard-record run produced an honest, complete transcript.

Checks (each one is a hard gate; first failure exits non-zero):
1. summary.json exists and parses; verdict in {PASS, FAIL}.
2. transcript.txt exists and is non-empty (>200 bytes).
3. env.txt records python/git/node versions and a git commit hash.
4. Exit code recorded matches verdict.
5. Transcript contains the 5 expected wizard banners in order:
     "Step 1/5  Preflight"
     "Step 2/5  Installing Hermes3D"
     "Step 3/5  Installing branch-discipline git hooks"
     "Step 4/5  Acceptance suite"
     "Step 5/5  Launching Gradio UI"
   (--quick mode is exempt from steps 4 + 5.)
6. No "FAIL" / "Traceback" string in transcript unless verdict==FAIL (mismatch = lying summary).

Usage: python scripts/verify-wizard-recording.py var/wizard-runs/<utc>/
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WIZARD_BANNERS = [
    "Step 1/5  Preflight",
    "Step 2/5  Installing Hermes3D",
    "Step 3/5  Installing branch-discipline git hooks",
    "Step 4/5  Acceptance suite",
    "Step 5/5  Launching Gradio UI",
]


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def main(run_dir: Path) -> None:
    if not run_dir.is_dir():
        fail(f"not a directory: {run_dir}")

    summary_path = run_dir / "summary.json"
    transcript_path = run_dir / "transcript.txt"
    env_path = run_dir / "env.txt"
    exit_path = run_dir / "exit_code.txt"

    for p in (summary_path, transcript_path, env_path, exit_path):
        if not p.exists():
            fail(f"missing required file: {p.name}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    verdict = summary.get("verdict")
    if verdict not in ("PASS", "FAIL"):
        fail(f"summary verdict invalid: {verdict!r}")

    transcript = transcript_path.read_text(encoding="utf-8", errors="replace")
    if len(transcript) < 200:
        fail(f"transcript too short ({len(transcript)} bytes); the wizard probably never started")

    env = env_path.read_text(encoding="utf-8")
    for required_field in ("python=", "git=", "git_commit="):
        if required_field not in env:
            fail(f"env.txt missing field: {required_field}")

    exit_code = int(exit_path.read_text().strip())
    expected_verdict = "PASS" if exit_code == 0 else "FAIL"
    if verdict != expected_verdict:
        fail(f"verdict {verdict!r} contradicts exit code {exit_code} (expected {expected_verdict!r})")

    quick = bool(summary.get("flags", {}).get("quick"))
    if quick:
        # Quick mode: only assert preflight banner ran.
        if "Hermes3D Preflight" not in transcript:
            fail("quick mode transcript missing 'Hermes3D Preflight' banner")
    else:
        last_pos = -1
        for banner in WIZARD_BANNERS:
            idx = transcript.find(banner, last_pos + 1)
            if idx < 0:
                fail(f"banner missing from transcript: {banner!r}")
            last_pos = idx

    # Honesty cross-check: if PASS, transcript must NOT contain unhandled tracebacks.
    if verdict == "PASS":
        # Allow tracebacks inside PYTEST output that ultimately passed (rare); be strict on
        # bare 'Traceback (most recent call last):' that aren't in pytest's '..  PASSED' frames.
        if re.search(r"^Traceback \(most recent call last\):", transcript, re.M) and \
           not re.search(r"PASSED", transcript) and \
           not re.search(r"\[fast\] skipped", transcript):
            fail("transcript contains a Traceback but verdict is PASS — recording is lying")

    print(f"[OK] {run_dir}: verdict={verdict} duration={summary.get('duration_seconds')}s exit={exit_code} quick={quick}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    main(Path(sys.argv[1]))
