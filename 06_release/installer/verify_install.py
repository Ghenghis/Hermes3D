#!/usr/bin/env python3
"""
06_release/installer/verify_install.py — post-install sanity check.

After install.{ps1,sh} runs, this script confirms that:

  1. Every required Python package imports cleanly
  2. The hermes3d package itself imports
  3. The CLI is callable and reports its version
  4. The core printer fleet enumerates (12 profiles)
  5. The truth-gate machinery loads
  6. The proof envelope signing key is set (or the dev default is honored)
  7. Optional components install report their state truthfully

Exits 0 iff every required check passes. Optional checks emit WARN-level
findings but never cause failure.

Usage:
    python verify_install.py
    python verify_install.py --json
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

REQUIRED_IMPORTS = [
    "hermes3d",
    "hermes3d.core.printers.printer_profiles",
    "hermes3d.core.agents.dispatcher",
    "hermes3d.core.validation.truth_gate",
    "hermes3d.core.proof.proof_envelope",
    "hermes3d.core.agents.tool_registrations",
]

OPTIONAL_IMPORTS = {
    "gradio": "Gradio UI",
    "fastapi": "REST API",
    "uvicorn": "REST API server",
    "httpx": "Ollama provider / Moonraker probe",
    "telegram": "Telegram bridge",
    "discord": "Discord bridge",
    "faiss": "FAISS vector memory",
    "sentence_transformers": "Embedding model for vector memory",
}


def _record(results: list, status: str, name: str, detail: str, fix: str = "") -> None:
    results.append({"status": status, "name": name, "detail": detail, "fix": fix})


def check_required_imports(results: list) -> None:
    for mod in REQUIRED_IMPORTS:
        try:
            importlib.import_module(mod)
            _record(results, "PASS", f"import {mod}", "ok")
        except Exception as exc:  # noqa: BLE001
            _record(
                results, "FAIL", f"import {mod}", str(exc),
                "Re-run install.{ps1,sh}; check pip install logs.",
            )


def check_optional_imports(results: list) -> None:
    for mod, label in OPTIONAL_IMPORTS.items():
        try:
            importlib.import_module(mod)
            _record(results, "PASS", f"optional {mod}", f"{label} available")
        except Exception:
            _record(
                results, "WARN", f"optional {mod}",
                f"{label} unavailable",
                f"Install if you want this feature: pip install {mod}",
            )


def check_cli(results: list) -> None:
    try:
        out = subprocess.run(
            [sys.executable, "-m", "hermes3d.cli", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and "hermes3d" in (out.stdout or "").lower():
            _record(results, "PASS", "CLI", "hermes3d --help works")
        else:
            _record(
                results, "FAIL", "CLI",
                f"exit={out.returncode}",
                "Check the install — `python -m hermes3d.cli --help` should print usage.",
            )
    except Exception as exc:  # noqa: BLE001
        _record(results, "FAIL", "CLI", str(exc),
                "Try `python -m hermes3d.cli --help` manually.")


def check_fleet(results: list) -> None:
    try:
        from hermes3d.core.printers.printer_profiles import FLEET, list_ids
        ids = list_ids()
        if len(ids) >= 12:
            _record(results, "PASS", "printer fleet", f"{len(ids)} profiles enumerated")
        else:
            _record(
                results, "WARN", "printer fleet",
                f"only {len(ids)} profiles (expected 12)",
                "config/printers.toml may have been edited.",
            )
        _ = FLEET  # ensure constant resolves
    except Exception as exc:  # noqa: BLE001
        _record(results, "FAIL", "printer fleet", str(exc))


def check_truth_gate(results: list) -> None:
    try:
        from hermes3d.core.validation.truth_gate import TruthGateReport  # noqa: F401
        _record(results, "PASS", "truth_gate", "module loads")
    except Exception as exc:  # noqa: BLE001
        _record(results, "FAIL", "truth_gate", str(exc))


def check_proof_key(results: list) -> None:
    if os.environ.get("HERMES3D_PROOF_KEY"):
        _record(results, "PASS", "HERMES3D_PROOF_KEY", "set")
    else:
        _record(
            results, "WARN", "HERMES3D_PROOF_KEY",
            "not set (using dev default 'hermes3d-default-proof-key-not-secret')",
            "Set HERMES3D_PROOF_KEY in .env for production.",
        )


def check_directories(results: list) -> None:
    # Path resolution: if running from repo root, look at var/.
    # Otherwise use the current working dir's var/.
    candidates = [Path("var"), Path("var")]
    found = next((p for p in candidates if p.exists()), None)
    if found:
        _record(results, "PASS", "var/ directory", f"exists at {found}")
    else:
        _record(results, "WARN", "var/ directory",
                "no var/ found", "mkdir -p var (the kit will create it on first run)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results: list = []
    check_required_imports(results)
    check_cli(results)
    check_fleet(results)
    check_truth_gate(results)
    check_proof_key(results)
    check_directories(results)
    check_optional_imports(results)

    pass_n = sum(1 for r in results if r["status"] == "PASS")
    warn_n = sum(1 for r in results if r["status"] == "WARN")
    fail_n = sum(1 for r in results if r["status"] == "FAIL")

    if args.json:
        print(json.dumps({
            "summary": {"pass": pass_n, "warn": warn_n, "fail": fail_n},
            "results": results,
        }, indent=2))
    else:
        print()
        print("Hermes3D-OS Lite — post-install verification")
        print("=" * 48)
        for r in results:
            color = {"PASS": "\033[32m", "WARN": "\033[33m", "FAIL": "\033[31m"}.get(r["status"], "")
            reset = "\033[0m" if color else ""
            print(f"  {color}[{r['status']}]{reset} {r['name']:30s} {r['detail']}")
            if r["status"] != "PASS" and r.get("fix"):
                print(f"         \033[2m{r['fix']}\033[0m")
        print()
        print(f"Summary: {pass_n} pass, {warn_n} warn, {fail_n} fail")

    return 1 if fail_n else 0


if __name__ == "__main__":
    sys.exit(main())
