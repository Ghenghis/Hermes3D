"""Skill memory — Hermes-style persistent learned skills.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §31 (Skill Memory)

The agent learns user-specific facts and reuses them across sessions.
Skills are typed, versioned, scope-tagged records — they are NOT raw
LLM context dumps and not arbitrary fact strings. Every skill has:

  - skill_id            stable UUID
  - skill_kind          enum (parameter_override, printer_quirk,
                              material_quirk, scheduling_pref,
                              user_preference, failure_pattern)
  - scope               which printer / material / time-of-day applies
  - body                structured payload (per-kind schema)
  - confidence          0..1 — how strongly the agent believes this
  - evidence_count      how many observations support it
  - source              "user_explicit" | "agent_observed" | "imported"
  - created_unix / updated_unix
  - last_applied_unix   when it was last looked up

Persistent storage is JSON-on-disk (atomic replace). Lookup by (kind,
scope) is O(N) — fine for the realistic case (low hundreds of skills).

Why this matters for the user's farm: the agent learns "ASA on D01 needs
chamber temp +5°C", "PLA on FLSUN T1_b stringes more than T1_a", "user
never starts prints after 11pm even though policy allows". These all
turn into skills that bias future dispatch and slicing decisions —
without ever putting the user's preferences in a system prompt.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0.0"


class SkillKind(str, enum.Enum):
    PARAMETER_OVERRIDE = "parameter_override"
    # body = {"slicer_setting": "first_layer_temperature", "value": 215}
    PRINTER_QUIRK = "printer_quirk"
    # body = {"observation": "Z-wobble at 250mm/s"}
    MATERIAL_QUIRK = "material_quirk"
    # body = {"observation": "stringes above 240C"}
    SCHEDULING_PREF = "scheduling_pref"
    # body = {"avoid_hours": [22, 23, 0, 1, 2, 3, 4, 5]}
    USER_PREFERENCE = "user_preference"
    # body = {"prefers": "matte finish over speed"}
    FAILURE_PATTERN = "failure_pattern"
    # body = {"trigger": "PETG on glass bed without glue", "rate": 0.45}


@dataclass(frozen=True)
class SkillScope:
    """Which contexts this skill applies to. ``None`` = "any"."""

    printer_id: str | None = None
    material: str | None = None
    quality_level: str | None = None  # draft / normal / fine
    hour_of_day: int | None = None  # 0-23

    def matches(
        self,
        *,
        printer_id: str | None = None,
        material: str | None = None,
        quality_level: str | None = None,
        hour_of_day: int | None = None,
    ) -> bool:
        if self.printer_id and self.printer_id != printer_id:
            return False
        if self.material and material:
            if self.material.upper() != material.upper():
                return False
        if self.quality_level and quality_level:
            if self.quality_level != quality_level:
                return False
        if self.hour_of_day is not None and hour_of_day is not None:
            if self.hour_of_day != hour_of_day:
                return False
        return True

    def specificity(self) -> int:
        """How many fields are non-None (more specific = higher priority)."""
        return sum(
            1
            for v in (self.printer_id, self.material, self.quality_level, self.hour_of_day)
            if v is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SkillScope":
        return cls(**d)


@dataclass
class Skill:
    skill_id: str
    skill_kind: SkillKind
    name: str
    scope: SkillScope
    body: dict[str, Any]
    confidence: float = 0.5
    evidence_count: int = 1
    source: str = "agent_observed"
    notes: str = ""
    created_unix: float = field(default_factory=time.time)
    updated_unix: float = field(default_factory=time.time)
    last_applied_unix: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["skill_kind"] = self.skill_kind.value
        d["scope"] = self.scope.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Skill":
        d = dict(d)
        d["skill_kind"] = SkillKind(d["skill_kind"])
        d["scope"] = SkillScope.from_dict(d["scope"])
        return cls(**d)


# =============================================================================


class SkillStore:
    """Persistent JSON-backed skill memory."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._skills: dict[str, Skill] = {}
        self._load()

    # ---- Persistence -------------------------------------------------------

    def _load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._skills = {}
                return
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(
                    f"Skill store schema mismatch: got "
                    f"{data.get('schema_version')!r}, expected {SCHEMA_VERSION!r}"
                )
            self._skills = {s["skill_id"]: Skill.from_dict(s) for s in data.get("skills", [])}

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "saved_unix": time.time(),
                "skills": [s.to_dict() for s in self._skills.values()],
            }
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self.path)

    # ---- CRUD --------------------------------------------------------------

    def add(
        self,
        *,
        skill_kind: SkillKind,
        name: str,
        scope: SkillScope,
        body: dict[str, Any],
        confidence: float = 0.5,
        source: str = "agent_observed",
        notes: str = "",
    ) -> Skill:
        with self._lock:
            sk = Skill(
                skill_id=uuid.uuid4().hex,
                skill_kind=skill_kind,
                name=name,
                scope=scope,
                body=dict(body),
                confidence=float(confidence),
                source=source,
                notes=notes,
            )
            self._skills[sk.skill_id] = sk
            self.save()
            return sk

    def get(self, skill_id: str) -> Skill:
        with self._lock:
            if skill_id not in self._skills:
                raise KeyError(skill_id)
            return self._skills[skill_id]

    def list(self, *, kind: SkillKind | None = None) -> list[Skill]:
        with self._lock:
            out = list(self._skills.values())
            if kind is not None:
                out = [s for s in out if s.skill_kind == kind]
            return sorted(out, key=lambda s: -s.updated_unix)

    def reinforce(self, skill_id: str, *, confidence_delta: float = 0.05, note: str = "") -> Skill:
        """Increment evidence count + bump confidence (capped at 1.0)."""
        with self._lock:
            sk = self.get(skill_id)
            sk.evidence_count += 1
            sk.confidence = min(1.0, sk.confidence + confidence_delta)
            sk.updated_unix = time.time()
            if note:
                sk.notes = (sk.notes + " | " + note) if sk.notes else note
            self.save()
            return sk

    def weaken(self, skill_id: str, *, confidence_delta: float = 0.10, note: str = "") -> Skill:
        """Bump confidence DOWN; if it falls below threshold, mark stale."""
        with self._lock:
            sk = self.get(skill_id)
            sk.confidence = max(0.0, sk.confidence - confidence_delta)
            sk.updated_unix = time.time()
            if note:
                sk.notes = (sk.notes + " | " + note) if sk.notes else note
            self.save()
            return sk

    def delete(self, skill_id: str) -> None:
        with self._lock:
            if skill_id in self._skills:
                del self._skills[skill_id]
                self.save()

    # ---- Lookup ------------------------------------------------------------

    def lookup(
        self,
        *,
        kind: SkillKind,
        printer_id: str | None = None,
        material: str | None = None,
        quality_level: str | None = None,
        hour_of_day: int | None = None,
        min_confidence: float = 0.0,
    ) -> list[Skill]:
        """Return matching skills, sorted by specificity then confidence.

        The most-specific, highest-confidence skill is first.
        """
        with self._lock:
            now = time.time()
            matches = []
            for sk in self._skills.values():
                if sk.skill_kind != kind:
                    continue
                if sk.confidence < min_confidence:
                    continue
                if not sk.scope.matches(
                    printer_id=printer_id,
                    material=material,
                    quality_level=quality_level,
                    hour_of_day=hour_of_day,
                ):
                    continue
                sk.last_applied_unix = now
                matches.append(sk)
            matches.sort(key=lambda s: (-s.scope.specificity(), -s.confidence))
            if matches:
                self.save()  # persist last_applied
            return matches

    def best(self, **lookup_args: Any) -> Skill | None:
        results = self.lookup(**lookup_args)
        return results[0] if results else None


__all__ = [
    "SCHEMA_VERSION",
    "Skill",
    "SkillKind",
    "SkillScope",
    "SkillStore",
]
