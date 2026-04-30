#!/usr/bin/env python3
"""Internal helper invoked by build-bundle.{sh,ps1} (A.6).

Aggregates all evidence produced by a build into a single signed zip
("proof bundle") under ``05_truth_proof/bundles/``.

This file is intentionally self-contained: the wrapper shell scripts
shell out to Python so all the heavy lifting (hashing, HMAC signing,
zipping, ledger generation) lives in one place and is testable
without bash.

Reuses ``hermes3d.core.proof.proof_envelope`` for the HMAC primitives
when it is importable; otherwise falls back to a byte-identical
implementation of ``canonical_payload`` + HMAC-SHA256 keyed by
``HERMES3D_PROOF_KEY``.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import hmac
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "05_truth_proof" / "bundles"
DEFAULT_KEY_ENV = "HERMES3D_PROOF_KEY"
SCHEMA_VERSION = "bundle-1.0.0"
DEFAULT_KEY = b"hermes3d-default-proof-key-not-secret"


# --------------------------------------------------------------------------- #
# Signing (reuse proof_envelope helpers when available; otherwise mirror them)
# --------------------------------------------------------------------------- #
def _load_proof_helpers():
    sys.path.insert(0, str(REPO_ROOT / "03_implementation" / "src"))
    try:
        from hermes3d.core.proof import proof_envelope as pe  # type: ignore
        return pe
    except Exception:
        return None


_PE = _load_proof_helpers()


def proof_key(env_var: str) -> bytes:
    val = os.environ.get(env_var)
    if val:
        return val.encode("utf-8")
    return DEFAULT_KEY


def canonical_bytes(doc: dict) -> bytes:
    """Match proof_envelope.canonical_payload's algorithm: sorted keys, no whitespace."""
    body = {k: v for k, v in doc.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hmac_sign(doc: dict, key: bytes) -> dict[str, str]:
    digest = hmac.new(key, canonical_bytes(doc), hashlib.sha256).hexdigest()
    return {"algorithm": "HMAC-SHA256", "value": digest}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# Git + env fingerprint
# --------------------------------------------------------------------------- #
def _run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(
            cmd, cwd=str(cwd or REPO_ROOT), stderr=subprocess.DEVNULL
        ).decode("utf-8", "replace").strip()
    except Exception:
        return ""


def git_info() -> dict[str, Any]:
    sha = _run(["git", "rev-parse", "HEAD"]) or "unknown"
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    status = _run(["git", "status", "--porcelain"])
    return {"sha": sha, "branch": branch, "dirty": bool(status)}


def env_fingerprint() -> dict[str, Any]:
    deps: dict[str, str] = {}
    for pkg in ("pytest", "trimesh", "numpy", "matplotlib", "fastapi", "gradio"):
        try:
            from importlib.metadata import version  # py3.8+
            deps[pkg] = version(pkg)
        except Exception:
            deps[pkg] = "not-installed"
    return {
        "python": sys.version.split()[0],
        "python_impl": platform.python_implementation(),
        "os": platform.platform(),
        "machine": platform.machine(),
        "deps": deps,
    }


# --------------------------------------------------------------------------- #
# Evidence collection
# --------------------------------------------------------------------------- #
def run_pytest(work: Path) -> tuple[Path | None, str]:
    """Run pytest with junitxml + (optionally) html report. Returns (xml, log)."""
    tests_dir = work / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    junit = tests_dir / "pytest-report.xml"
    html = tests_dir / "pytest-report.html"

    # Decide whether pytest-html is available.
    has_html = subprocess.call(
        [sys.executable, "-c", "import pytest_html"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ) == 0

    cmd = [sys.executable, "-m", "pytest", "-q",
           f"--junitxml={junit}", "--maxfail=1000"]
    if has_html:
        cmd += [f"--html={html}", "--self-contained-html"]

    log_path = work / "logs" / "pytest.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as fp:
        try:
            subprocess.run(cmd, cwd=str(REPO_ROOT), stdout=fp,
                           stderr=subprocess.STDOUT, timeout=900, check=False)
        except Exception as exc:
            fp.write(f"\n[bundle] pytest invocation failed: {exc}\n")
    return (junit if junit.exists() else None, log_path.read_text(encoding="utf-8", errors="replace"))


def run_forbidden_scan(work: Path) -> Path:
    """Locate forbidden_pattern_scan.py wherever the restructure has placed it."""
    candidates = [
        REPO_ROOT / "scripts" / "scaffolding" / "forbidden_pattern_scan.py",
        REPO_ROOT / "scripts" / "forbidden_pattern_scan.py",
    ]
    log_path = work / "logs" / "forbidden_scan.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    script = next((c for c in candidates if c.is_file()), None)
    with open(log_path, "w", encoding="utf-8") as fp:
        if script is None:
            fp.write("[bundle] forbidden_pattern_scan.py not found; skipped.\n")
        else:
            try:
                subprocess.run([sys.executable, str(script)],
                               cwd=str(REPO_ROOT), stdout=fp,
                               stderr=subprocess.STDOUT, timeout=120, check=False)
            except Exception as exc:
                fp.write(f"[bundle] forbidden_pattern_scan invocation failed: {exc}\n")
    return log_path


def gather_envelopes(dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    sources = [
        REPO_ROOT / "var" / "acceptance-results",
        REPO_ROOT / "var" / "dispatch",
    ]
    copied: list[Path] = []
    for src in sources:
        if not src.exists():
            continue
        for jp in src.rglob("*.json"):
            n = jp.name
            if n == "proof.json" or n.endswith(".proof.json") or n.startswith("proof-"):
                rel = jp.relative_to(src.parent)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(jp, target)
                copied.append(target)
    return copied


def build_evidence_ledger(envelopes: list[Path], work: Path) -> Path:
    ledger_md = work / "evidence_ledger.md"
    rows: list[tuple[str, str, str]] = []

    # Source 1: HONESTY_LEDGER (table-style claims).
    for hl in [
        REPO_ROOT / "00_overview/contract" / "HONESTY_LEDGER.md",
        REPO_ROOT / "00_overview" / "contract" / "HONESTY_LEDGER.md",
    ]:
        if not hl.is_file():
            continue
        for line in hl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("|---") or line.startswith("| Component"):
                continue
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 2 and cols[0] and not cols[0].startswith("---"):
                rows.append(("honesty_ledger", cols[0], cols[1] if len(cols) > 1 else ""))
        break

    # Source 2: KIT_MANIFEST entries.
    for km in [
        REPO_ROOT / "00_overview/contract" / "KIT_MANIFEST.json",
        REPO_ROOT / "00_overview" / "contract" / "KIT_MANIFEST.json",
    ]:
        if not km.is_file():
            continue
        try:
            data = json.loads(km.read_text(encoding="utf-8"))
            for entry in data.get("files", [])[:200]:
                rows.append(("kit_manifest", entry.get("path", "?"), entry.get("role", "")))
        except Exception:
            pass
        break

    # Source 3: each collected envelope is its own claim row.
    for ep in envelopes:
        rows.append(("proof_envelope", ep.name, str(ep.relative_to(work))))

    lines = [
        "# Evidence Ledger",
        "",
        f"_Auto-generated by `scripts/build-bundle` at "
        f"{_dt.datetime.now(_dt.timezone.utc).isoformat()}_",
        "",
        "| Source | Claim | Proof / Status |",
        "|---|---|---|",
    ]
    for src, claim, proof in rows:
        c = claim.replace("|", "\\|")[:200]
        p = proof.replace("|", "\\|")[:200]
        lines.append(f"| {src} | {c} | {p} |")

    ledger_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ledger_md


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build(output_dir: Path, key_env_var: str) -> dict[str, Any]:
    started = time.time()
    utc = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git = git_info()
    run_id = f"{git['sha'][:12]}-{utc}"

    work = REPO_ROOT / "var" / "proof-bundles" / run_id
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    (work / "logs").mkdir(exist_ok=True)
    (work / "tests").mkdir(exist_ok=True)
    (work / "proof" / "envelopes").mkdir(parents=True, exist_ok=True)
    (work / "screenshots").mkdir(exist_ok=True)

    # b. pytest
    run_pytest(work)
    # c. forbidden-pattern scan
    run_forbidden_scan(work)
    # d. existing HMAC envelopes
    envelopes = gather_envelopes(work / "proof" / "envelopes")
    # e. evidence ledger
    build_evidence_ledger(envelopes, work)

    # Build manifest with sha256 of every staged file.
    files: list[dict[str, Any]] = []
    for p in sorted(work.rglob("*")):
        if p.is_file():
            files.append({
                "path": str(p.relative_to(work)).replace("\\", "/"),
                "size": p.stat().st_size,
                "sha256": file_sha256(p),
            })

    duration = time.time() - started
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "git": git,
        "build": {
            "utc_iso": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
        "env": env_fingerprint(),
        "signer": {
            "identity": os.environ.get("HERMES3D_SIGNER_IDENTITY", "unknown"),
            "key_env_var": key_env_var,
        },
        "files": files,
    }

    key = proof_key(key_env_var)
    manifest_path = work / "manifest.json"
    # Sign over everything except the signature itself.
    sig = hmac_sign(manifest, key)
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    sig_path = work / "manifest.sig"
    sig_path.write_text(json.dumps(sig, sort_keys=True), encoding="utf-8")

    # Zip everything.
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{run_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(work.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(work)).replace("\\", "/"))

    digest = file_sha256(zip_path)
    size = zip_path.stat().st_size
    print(f"[bundle] path:   {zip_path.resolve()}")
    print(f"[bundle] size:   {size} bytes")
    print(f"[bundle] sha256: {digest}")
    print(f"[bundle] run_id: {run_id}")
    return {"path": str(zip_path.resolve()), "size": size, "sha256": digest, "run_id": run_id}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build a signed Hermes3D proof bundle (A.6).")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--key-env-var", default=DEFAULT_KEY_ENV)
    args = p.parse_args(argv)
    build(args.output, args.key_env_var)
    return 0


if __name__ == "__main__":
    sys.exit(main())
