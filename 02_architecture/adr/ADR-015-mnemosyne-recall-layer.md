# ADR-015: Mnemosyne recall layer for Hermes3D agents

**Status:** Proposed
**Date:** 2026-05-03

## Context

Hermes3D agents (orchestrator, dispatcher, mesh-repair, preflight) repeatedly solve the same problems on the same printer × material × quality combinations. Useful empirical signal — "this combination needed flow=92%", "prusa-mk4-02 needs Z-offset -0.05 with PEI" — is currently lost between sessions because the deterministic agents don't accumulate experience.

The user's `rakaarwaky/mnemosyne` library (PyPI: `mnemosyne-memory`, version 2.x at adoption) provides a local-first SQLite-backed memory store with FTS5 + vector search, sub-millisecond, zero-cloud, private.

## Decision

Adopt `mnemosyne-memory>=2.0,<3` as a **recall layer** for Hermes3D agents. Recall is **NOT canonical**.

- The append-only evidence ledger at `var/proofs/...ndjson` remains the canonical source of truth for every dispatch / acceptance / release decision.
- Mnemosyne stores non-canonical hints — printer quirks observed, agent failure patterns, reinforcement signals from successful prints.
- Decisions cite recall hints, but never authoritatively rely on them. Deterministic logic dominates; recall biases the score.
- When Mnemosyne is unavailable (package not installed, DB locked, import error), agents continue with deterministic logic — degraded but functional. Soft-import wrapper at `core/memory/mnemosyne_recall.py` returns safe defaults.

## Rationale & Consequences

**Positive:**
- Agents accumulate empirical knowledge across sessions (currently zero).
- Dispatcher's printer × material × quality scoring becomes adaptive without breaking the deterministic baseline.
- Privacy posture preserved (local SQLite, zero cloud).
- License compatibility (MIT) — fits Hermes3D's MIT.

**Negative:**
- Adds a SQLite file under `var/` (gitignored).
- New optional dependency surface (`mnemosyne-memory`).
- Dispatcher purity contract requires upstream injection of recall hints (no I/O in scoring function).

## Alternatives considered

- **No memory layer** — rejected: agents repeatedly solve the same problems.
- **Cloud memory (Pinecone, Weaviate, etc.)** — rejected: privacy posture requires local-first.
- **Make memory canonical** — rejected: would shift the source of truth away from the evidence ledger; auditability suffers.
- **Pure in-process dict** — rejected: doesn't persist across sessions.

## References

- `rakaarwaky/mnemosyne` — https://github.com/rakaarwaky/mnemosyne
- PyPI: https://pypi.org/project/mnemosyne-memory/
- Soft-import wrapper: `03_implementation/src/hermes3d/core/memory/mnemosyne_recall.py`
- Evidence ledger: `var/proofs/*.ndjson` (canonical)
