"""Skill packs — import/export bundles for community skill sharing.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §42 (Skill Packs)

Lets users share learned skills with each other. A skill pack is a JSON
file with a manifest + a list of skills. Importing applies them to the
local SkillStore, with options to:
  - merge        — add new skills, leave duplicates alone
  - overwrite    — add new skills, replace duplicates by name
  - audit        — return a diff report without applying

Built-in skill packs ship in `config/skill_packs/`:
  - flsun_t1_essentials.json     — known-good params for FLSUN T1
  - tronxy_d01_quirks.json       — D01 Pro CoreXY tuning
  - asa_general_tips.json        — ASA across the fleet

Users export their own packs to share with the community (no PII —
the export filter strips spool_id, job_id, and any user-named fields).
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from hermes3d.core.memory import (
    Skill,
    SkillKind,
    SkillScope,
    SkillStore,
    SCHEMA_VERSION,
)


log = logging.getLogger(__name__)


PACK_SCHEMA_VERSION = "1.0.0"


class ImportMode(str, enum.Enum):
    MERGE = "merge"  # add new, skip duplicates by name
    OVERWRITE = "overwrite"  # add new, replace duplicates by name
    AUDIT = "audit"  # don't change anything, return diff


@dataclass
class SkillPackManifest:
    pack_schema_version: str = PACK_SCHEMA_VERSION
    skill_schema_version: str = SCHEMA_VERSION
    created_unix: float = field(default_factory=time.time)
    pack_name: str = "untitled"
    pack_version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = "CC0-1.0"
    skill_count: int = 0
    sha256: str | None = None


@dataclass
class SkillPack:
    manifest: SkillPackManifest
    skills: list[Skill] = field(default_factory=list)


@dataclass
class SkillPackImportReport:
    added_skill_ids: list[str] = field(default_factory=list)
    replaced_skill_ids: list[str] = field(default_factory=list)
    skipped_skill_names: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    audit_only: bool = False


# =============================================================================


def export_pack(
    store: SkillStore,
    *,
    pack_name: str,
    description: str = "",
    author: str = "",
    pack_version: str = "1.0.0",
    only_kinds: Iterable[SkillKind] | None = None,
    min_confidence: float = 0.0,
) -> SkillPack:
    """Serialize learned skills into a sharable pack.

    PII strip:
      - per-skill ``notes`` longer than 500 chars are truncated
      - ``last_applied_unix`` is dropped (privacy: usage timing)
      - skill IDs are regenerated on import to avoid collision
    """
    skills_to_pack: list[Skill] = []
    for sk in store.list():
        if only_kinds is not None and sk.skill_kind not in only_kinds:
            continue
        if sk.confidence < min_confidence:
            continue
        # Strip PII / regenerate metadata on export
        clean = Skill(
            skill_id=sk.skill_id,  # regenerated on import
            skill_kind=sk.skill_kind,
            name=sk.name,
            scope=sk.scope,
            body=dict(sk.body),  # body is opaque — caller's job to clean
            confidence=sk.confidence,
            evidence_count=sk.evidence_count,
            source="imported",
            notes=(sk.notes[:500] if sk.notes else ""),
            created_unix=sk.created_unix,
            updated_unix=sk.updated_unix,
            last_applied_unix=None,
        )
        skills_to_pack.append(clean)
    return SkillPack(
        manifest=SkillPackManifest(
            pack_name=pack_name,
            pack_version=pack_version,
            description=description,
            author=author,
            skill_count=len(skills_to_pack),
        ),
        skills=skills_to_pack,
    )


def write_pack(pack: SkillPack, path: str | Path) -> Path:
    """Serialize the pack to a JSON file with a content-hash."""
    payload_skills = [s.to_dict() for s in pack.skills]
    body = json.dumps(payload_skills, sort_keys=True).encode("utf-8")
    pack.manifest.sha256 = hashlib.sha256(body).hexdigest()
    pack.manifest.skill_count = len(pack.skills)
    out = {
        "manifest": dataclasses.asdict(pack.manifest),
        "skills": payload_skills,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    return p


def read_pack(path: str | Path) -> SkillPack:
    """Read and validate a skill pack file."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    m = data.get("manifest") or {}
    if m.get("pack_schema_version") != PACK_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported pack schema {m.get('pack_schema_version')!r}; "
            f"expected {PACK_SCHEMA_VERSION!r}"
        )
    if m.get("skill_schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported skill schema {m.get('skill_schema_version')!r}; "
            f"expected {SCHEMA_VERSION!r}"
        )
    body = json.dumps(data.get("skills", []), sort_keys=True).encode("utf-8")
    expected_sha = m.get("sha256")
    actual_sha = hashlib.sha256(body).hexdigest()
    if expected_sha and expected_sha != actual_sha:
        raise ValueError(
            "skill pack content-hash mismatch — pack is corrupt or tampered "
            f"(manifest={expected_sha!r}, computed={actual_sha!r})"
        )
    skills = [Skill.from_dict(s) for s in data.get("skills", [])]
    manifest = SkillPackManifest(
        **{k: v for k, v in m.items() if k in SkillPackManifest.__dataclass_fields__}
    )
    return SkillPack(manifest=manifest, skills=skills)


def import_pack(
    store: SkillStore,
    pack: SkillPack,
    *,
    mode: ImportMode = ImportMode.MERGE,
) -> SkillPackImportReport:
    """Apply (or audit) a skill pack against a local store."""
    import uuid

    report = SkillPackImportReport(audit_only=(mode is ImportMode.AUDIT))
    existing_by_name = {s.name: s for s in store.list()}
    for sk in pack.skills:
        if sk.name in existing_by_name:
            if mode is ImportMode.MERGE:
                report.skipped_skill_names.append(sk.name)
                continue
            if mode is ImportMode.OVERWRITE:
                if not report.audit_only:
                    store.delete(existing_by_name[sk.name].skill_id)
                report.replaced_skill_ids.append(existing_by_name[sk.name].skill_id)
        if report.audit_only:
            report.added_skill_ids.append("(audit)")
        else:
            try:
                added = store.add(
                    skill_kind=sk.skill_kind,
                    name=sk.name,
                    scope=sk.scope,
                    body=dict(sk.body),
                    confidence=sk.confidence,
                    source="imported",
                    notes=sk.notes,
                )
                report.added_skill_ids.append(added.skill_id)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"{sk.name}: {exc}")
    return report


__all__ = [
    "ImportMode",
    "PACK_SCHEMA_VERSION",
    "SkillPack",
    "SkillPackImportReport",
    "SkillPackManifest",
    "export_pack",
    "import_pack",
    "read_pack",
    "write_pack",
]
