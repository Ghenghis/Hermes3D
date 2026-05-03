"""Hermes3D persistent skill memory — Hermes-style cross-session learning.

The :class:`SkillStore` is the canonical, exact-match learning layer.
:mod:`mnemosyne_recall` is an OPTIONAL soft-imported recall layer that
surfaces fuzzy hints from prior runs; it is **not** the source of truth
for any decision (see ADR-014).
"""

from .mnemosyne_recall import (
    DEFAULT_RECALL_DB,
    MnemosyneRecall,
    RecallHint,
    default_recall,
)
from .skill_store import (
    SCHEMA_VERSION,
    Skill,
    SkillKind,
    SkillScope,
    SkillStore,
)

__all__ = [
    "DEFAULT_RECALL_DB",
    "MnemosyneRecall",
    "RecallHint",
    "SCHEMA_VERSION",
    "Skill",
    "SkillKind",
    "SkillScope",
    "SkillStore",
    "default_recall",
]
