"""Generate KIT_MANIFEST.json with file inventory and tier annotations.

Run from repo root:
    python 00-CONTRACT/_generate_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "var", ".git"}

# (path_glob, tier, role) — first match wins
TIER_RULES: list[tuple[str, str, str]] = [
    # Contract layer
    ("00-CONTRACT/", "runnable", "contract_doc"),
    # Architecture / contracts (mostly empty in v5; markers for v5.1)
    ("01-ARCHITECTURE/diagrams/", "spec", "diagram"),
    ("01-ARCHITECTURE/contracts/", "spec", "contract_schema"),
    ("01-ARCHITECTURE/", "spec", "architecture_doc"),
    # Source code — every module under src/hermes3d has a real
    # implementation backed by tests in v5; classify as runnable.
    ("02-SCAFFOLDING/src/hermes3d/", "runnable", "module"),
    ("02-SCAFFOLDING/tests/", "runnable", "test"),
    ("02-SCAFFOLDING/config/klipper/", "runnable", "klipper_config"),
    ("02-SCAFFOLDING/config/", "runnable", "config"),
    ("02-SCAFFOLDING/scripts/", "runnable", "script"),
    ("02-SCAFFOLDING/.github/workflows/", "runnable", "ci_workflow"),
    ("02-SCAFFOLDING/", "runnable", "infrastructure"),
    # Proof system
    ("03-PROOF-SYSTEM/", "runnable", "proof"),
    # Test case
    ("04-TEST-CASE-DESK-ORGANIZER/", "runnable", "acceptance_test"),
    # Installer
    ("05-INSTALLER/", "runnable", "installer"),
    # Docs
    ("07-DOCS/", "runnable", "doc"),
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
            if rel in {"00-CONTRACT/KIT_MANIFEST.json",
                       "00-CONTRACT/_generate_manifest.py"}:
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
    out = REPO_ROOT / "00-CONTRACT" / "KIT_MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=False), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Files: {manifest['summary']['total_files']}, "
          f"bytes: {manifest['summary']['total_bytes']}")
    print(f"By tier: {manifest['summary']['by_tier']}")
    print(f"By role: {manifest['summary']['by_role']}")


if __name__ == "__main__":
    main()
