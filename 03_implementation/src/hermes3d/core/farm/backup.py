"""Backup / restore utility.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §29 (Backup & Restore)

Periodic snapshot of the user's persistent state:
  - queue.json
  - spools.json
  - history.jsonl
  - acceptance-results/ (proof bundles)

Bundle is a .tar.gz with a manifest.json describing what's inside.
Restoration is non-destructive — it writes to a target directory and
never overwrites a non-empty target without an explicit ``overwrite=True``
flag.

Usage::

    from hermes3d.core.farm.backup import create_backup, restore_backup
    bundle_path = create_backup(state_dir="./var", out_dir="./backups")
    restore_backup(bundle_path, target_dir="./var-restored")
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import tarfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0.0"


@dataclass
class BackupManifest:
    schema_version: str = SCHEMA_VERSION
    created_unix: float = field(default_factory=time.time)
    files: list[dict[str, Any]] = field(default_factory=list)
    state_dir: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_state_files(state_dir: Path, extra_globs: Iterable[str] = ()) -> list[Path]:
    """Files that are part of a backup."""
    candidates: list[Path] = []
    for name in ("queue.json", "spools.json", "history.jsonl"):
        p = state_dir / name
        if p.exists():
            candidates.append(p)
    accept = state_dir / "acceptance-results"
    if accept.exists():
        for p in accept.rglob("*"):
            if p.is_file():
                candidates.append(p)
    for g in extra_globs:
        for p in state_dir.glob(g):
            if p.is_file() and p not in candidates:
                candidates.append(p)
    return candidates


def create_backup(
    *, state_dir: str | Path, out_dir: str | Path, extra_globs: Iterable[str] = (), notes: str = ""
) -> Path:
    """Create a .tar.gz snapshot of state_dir's persistent files.

    Returns the path to the created bundle.
    """
    state = Path(state_dir).resolve()
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    files = _iter_state_files(state, extra_globs)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    bundle_name = f"hermes3d-backup-{timestamp}.tar.gz"
    bundle_path = out / bundle_name

    manifest = BackupManifest(state_dir=str(state), notes=notes)
    manifest.files = [
        {"path": str(f.relative_to(state)), "size_bytes": f.stat().st_size, "sha256": _sha256(f)}
        for f in files
    ]

    with tarfile.open(bundle_path, "w:gz") as tar:
        for f in files:
            tar.add(f, arcname=str(f.relative_to(state)))
        # Add manifest last
        manifest_bytes = json.dumps(manifest.to_dict(), indent=2, sort_keys=True).encode("utf-8")
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest_bytes)
        info.mtime = int(time.time())
        import io

        tar.addfile(info, io.BytesIO(manifest_bytes))

    return bundle_path


def restore_backup(
    bundle_path: str | Path, *, target_dir: str | Path, overwrite: bool = False
) -> BackupManifest:
    """Extract a backup bundle into target_dir.

    Returns the loaded BackupManifest. Raises FileExistsError if target
    is non-empty and overwrite=False.
    """
    bundle = Path(bundle_path).resolve()
    target = Path(target_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if not overwrite and any(target.iterdir()):
        raise FileExistsError(f"target_dir {target} is not empty (use overwrite=True)")
    with tarfile.open(bundle, "r:gz") as tar:
        # Validate manifest first
        manifest_member = None
        for member in tar.getmembers():
            if member.name == "manifest.json":
                manifest_member = member
                break
        if manifest_member is None:
            raise ValueError("Backup is missing manifest.json")
        manifest_data = json.loads(tar.extractfile(manifest_member).read().decode("utf-8"))
        if manifest_data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                f"Backup schema {manifest_data.get('schema_version')!r} != {SCHEMA_VERSION!r}"
            )
        # Extract everything except the manifest
        for member in tar.getmembers():
            if member.name == "manifest.json":
                continue
            # Defensive: filter against path traversal
            if member.name.startswith(("/", "..")) or ".." in Path(member.name).parts:
                raise ValueError(f"Refusing unsafe member: {member.name}")
            tar.extract(member, path=target, filter="data")

    return BackupManifest(
        **{k: v for k, v in manifest_data.items() if k in BackupManifest.__dataclass_fields__}
    )


__all__ = [
    "BackupManifest",
    "SCHEMA_VERSION",
    "create_backup",
    "restore_backup",
]
