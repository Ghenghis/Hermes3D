#!/usr/bin/env python3
"""Create a signed UI e2e proof bundle for TESTS-PROOF artifacts."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import platform
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

SCHEMA_VERSION = "bundle-1.0.0"
DEFAULT_KEY = b"hermes3d-default-proof-key-not-secret"


def canonical(doc: dict[str, Any]) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(args: list[str], cwd: Path, default: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return default


def add_tree(files: list[tuple[Path, str]], root: Path, bundle_prefix: str) -> None:
    if not root.exists():
        return
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        files.append((path, f"{bundle_prefix}/{rel}"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_ledger(files: list[tuple[Path, str]]) -> str:
    rows = [
        "# Evidence Ledger",
        "",
        "| claim | proof_type | bundle_path |",
        "|---|---|---|",
    ]
    for _, rel in sorted(files, key=lambda item: item[1]):
        if rel.endswith("results.json"):
            rows.append(f"| playwright_e2e_results | test_report | {rel} |")
        elif rel.endswith(".png"):
            rows.append(f"| ui_screenshot | screenshot | {rel} |")
        elif rel.endswith(".md"):
            rows.append(f"| readiness_notes | document | {rel} |")
        else:
            rows.append(f"| supporting_artifact | file | {rel} |")
    rows.append("")
    return "\n".join(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root", default=None, help="Repository root. Defaults to script ancestor."
    )
    parser.add_argument("--test-results", default="03_implementation/ui/test-results/e2e")
    parser.add_argument("--proof-root", default="03_implementation/proof")
    parser.add_argument("--output", default="03_implementation/proof")
    parser.add_argument("--key-env-var", default="HERMES3D_PROOF_KEY")
    return parser.parse_args()


def main() -> int:
    started = time.time()
    args = parse_args()
    script_path = Path(__file__).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else script_path.parents[2]
    test_results = (repo_root / args.test_results).resolve()
    proof_root = (repo_root / args.proof_root).resolve()
    output_root = (repo_root / args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    sha = git_value(["rev-parse", "HEAD"], repo_root, "unknown")
    branch = git_value(["rev-parse", "--abbrev-ref", "HEAD"], repo_root, "unknown")
    dirty = bool(git_value(["status", "--porcelain"], repo_root, ""))
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{sha[:12]}-{utc}" if sha != "unknown" else f"unknown-{utc}"

    with TemporaryDirectory(prefix="h3d-ui-proof-") as tmp_name:
        tmp = Path(tmp_name)
        files: list[tuple[Path, str]] = []
        add_tree(files, test_results, "tests/e2e")

        readiness = proof_root / "TESTS_PROOF_READINESS.md"
        if readiness.exists():
            files.append((readiness, "proof/TESTS_PROOF_READINESS.md"))

        ledger_path = tmp / "evidence_ledger.md"
        write_text(ledger_path, build_ledger(files))
        files.append((ledger_path, "evidence_ledger.md"))

        manifest_files = [
            {"path": rel, "size": src.stat().st_size, "sha256": sha256_file(src)}
            for src, rel in sorted(files, key=lambda item: item[1])
        ]

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "git": {"sha": sha, "branch": branch, "dirty": dirty},
            "build": {
                "utc_iso": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "duration_seconds": round(time.time() - started, 3),
            },
            "env": {
                "python": platform.python_version(),
                "python_impl": platform.python_implementation(),
                "os": platform.platform(),
                "machine": platform.machine(),
                "deps": {},
            },
            "signer": {
                "identity": os.environ.get("HERMES3D_SIGNER_IDENTITY", "unknown"),
                "key_env_var": args.key_env_var,
            },
            "files": manifest_files,
        }
        key = os.environ.get(args.key_env_var)
        key_bytes = key.encode("utf-8") if key else DEFAULT_KEY
        sig = {
            "algorithm": "HMAC-SHA256",
            "value": hmac.new(key_bytes, canonical(manifest), hashlib.sha256).hexdigest(),
        }

        manifest_path = tmp / "manifest.json"
        sig_path = tmp / "manifest.sig"
        write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        write_text(sig_path, json.dumps(sig, indent=2, sort_keys=True) + "\n")

        bundle_path = output_root / f"{run_id}.zip"
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(manifest_path, "manifest.json")
            zf.write(sig_path, "manifest.sig")
            for src, rel in files:
                zf.write(src, rel)

    digest = sha256_file(bundle_path)
    print(
        json.dumps(
            {"bundle": str(bundle_path), "sha256": digest, "size": bundle_path.stat().st_size},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
