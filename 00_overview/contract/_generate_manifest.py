"""Generate KIT_MANIFEST.json with file inventory and tier annotations.

Run from repo root:
    python 00_overview/contract/_generate_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "var", ".git"}

# (path_glob, tier, role) — first match wins
TIER_RULES: list[tuple[str, str, str]] = [
    # Contract layer
    ("00_overview/contract/", "runnable", "contract_doc"),
    # Architecture / contracts (mostly empty in v5; markers for v5.1)
    ("02_architecture/diagrams/", "spec", "diagram"),
    ("02_architecture/contracts/", "spec", "contract_schema"),
    ("02_architecture/", "spec", "architecture_doc"),
    # Source code — every module under src/hermes3d has a real
    # implementation backed by tests in v5; classify as runnable.
    ("03_implementation/src/hermes3d/", "runnable", "module"),
    ("04_testing/pytest/", "runnable", "test"),
    ("03_implementation/config/klipper/", "runnable", "klipper_config"),
    ("03_implementation/config/", "runnable", "config"),
    ("scripts/scaffolding/", "runnable", "script"),
    (".github/workflows/", "runnable", "ci_workflow"),
    ("03_implementation/", "runnable", "infrastructure"),
    # Proof system
    ("05_truth_proof/", "runnable", "proof"),
    # Test case
    ("04_testing/acceptance/", "runnable", "acceptance_test"),
    # Installer
    ("06_release/installer/", "runnable", "installer"),
    # Docs
    ("01_requirements/", "runnable", "doc"),
    # Top-level
    ("env/", "runnable", "env_template"),
    ("pyproject.toml", "runnable", "config"),
    ("requirements.txt", "runnable", "deps"),
    ("requirements-dev.txt", "runnable", "deps"),
    (".gitignore", "runnable", "vcs_config"),
    (".editorconfig", "runnable", "editor_config"),
    ("run.bat", "runnable", "script"),
]


def classify(rel_path: str) -> tuple[str, str]:
    for prefix, tier, role in TIER_RULES:
        if prefix.endswith("/"):
            if rel_path.startswith(prefix):
                return tier, role
        else:
            if rel_path == prefix:
                return tier, role
    return "spec", "unknown"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files() -> list[dict]:
    files = []
    for root, dirs, names in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in names:
            full = Path(root) / name
            if full.is_symlink():
                continue
            rel = full.relative_to(REPO_ROOT).as_posix()
            # Skip the manifest itself + the generator
            if rel in {"00_overview/contract/KIT_MANIFEST.json",
                       "00_overview/contract/_generate_manifest.py"}:
                continue
            tier, role = classify(rel)
            files.append({
                "path": rel,
                "size_bytes": full.stat().st_size,
                "sha256": sha256(full),
                "tier": tier,
                "role": role,
            })
    files.sort(key=lambda f: f["path"])
    return files


def summarise(files: list[dict]) -> dict:
    by_tier: dict[str, int] = {}
    by_role: dict[str, int] = {}
    total_bytes = 0
    for f in files:
        by_tier[f["tier"]] = by_tier.get(f["tier"], 0) + 1
        by_role[f["role"]] = by_role.get(f["role"], 0) + 1
        total_bytes += f["size_bytes"]
    return {
        "total_files": len(files),
        "total_bytes": total_bytes,
        "by_tier": by_tier,
        "by_role": by_role,
    }


def main() -> None:
    files = collect_files()
    manifest = {
        "manifest_version": "1.0.0",
        "kit": "Hermes3D-OS Lite v5 Contract Kit",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": summarise(files),
        "files": files,
    }
    out = REPO_ROOT / "00_overview/contract" / "KIT_MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=False), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Files: {manifest['summary']['total_files']}, "
          f"bytes: {manifest['summary']['total_bytes']}")
    print(f"By tier: {manifest['summary']['by_tier']}")
    print(f"By role: {manifest['summary']['by_role']}")


if __name__ == "__main__":
    main()
