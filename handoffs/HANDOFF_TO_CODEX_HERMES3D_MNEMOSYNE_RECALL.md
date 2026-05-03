# HANDOFF_TO_CODEX — Mnemosyne recall layer (Task 4b)

> **Status:** READY for Codex pickup.
>
> **Sequence position:** Task 4b in overnight queue (after Task 4a).
>
> **Owner:** `codex-impl-07`.
>
> **Estimated time:** 1.5-3 hours.
>
> **Audit history:** parent brief failed audit on PyPI name mismatch; this split corrects it (`mnemosyne-memory`, NOT `mnemosyne`) and confirms the package IS pip-installable. The §9 BEAM/Erlang fallback branch from the parent brief is dead code and removed.

---

## 1. Mission

Add `mnemosyne-memory` (the user's local-first SQLite + FTS5 + vector-search memory library at `rakaarwaky/mnemosyne`) as a **recall layer** for Hermes3D's agents. Recall hints feed the dispatcher's scoring + the auto-orient agent's decisions.

**Critical contract:** Mnemosyne is a recall layer. The evidence ledger (`var/proofs/...`) remains the canonical source of truth. Mnemosyne stores NON-canonical hints — printer quirks observed, agent failure patterns, "this material × this printer needs flow=92%" reinforcement signals.

NO LLM provider work. NO UI work. NO port monitor. Those are 4a and 4c.

---

## 2. Claim

```text
hermes_pick_task
  owner=codex-impl-07
  prefer_task_id=CP-HERMES3D-MNEMOSYNE-RECALL
```

Or fallback: `taskId=CP-HERMES3D-MNEMOSYNE-RECALL`, `title=Mnemosyne local-first memory recall layer`, `reason=Agent recall hints; not source of truth. Split 2/3 of LOCAL-INTELLIGENCE.`

---

## 3. Branch

`feat/cp-hermes3d-mnemosyne-recall` from `develop`.

---

## 4. Lock these files

```text
hermes_lock_files
  owner=codex-impl-07
  taskId=CP-HERMES3D-MNEMOSYNE-RECALL
  ttlMinutes=180
  files=[
    "03_implementation/src/hermes3d/core/memory/__init__.py",
    "03_implementation/src/hermes3d/core/memory/mnemosyne_recall.py",
    "03_implementation/src/hermes3d/core/agents/orchestrator.py",
    "03_implementation/src/hermes3d/core/agents/dispatcher.py",
    "04_testing/pytest/integration/test_mnemosyne_recall.py",
    "00_overview/contract/HONESTY_LEDGER.md",
    "02_architecture/adr/ADR-016-mnemosyne-recall-layer.md",
    "pyproject.toml",
    "requirements.txt"
  ]
```

**Confirmed existing on develop:** `core/memory/__init__.py` (yes), `core/agents/orchestrator.py` (yes), `core/agents/dispatcher.py` (yes — it's the existing dispatch agent), `pyproject.toml`, `requirements.txt`, `HONESTY_LEDGER.md`.

**Confirmed NEW:** `core/memory/mnemosyne_recall.py`, the test file, ADR-016 (skipping ADR-015 which is reserved for Task 4a's LLM-providers ADR — confirm in Task 4a's PR before claiming -016).

If ADR-016 conflicts because Task 4a hasn't merged yet, use ADR-017 instead. Verify ADR availability via `git ls-tree origin/develop -- 02_architecture/adr/` before locking.

---

## 5. Implementation contract

### 5.1 PyPI dependency

**`pyproject.toml`** + **`requirements.txt`** — add:

```toml
mnemosyne-memory>=0.1,<2.0
```

The package name is `mnemosyne-memory` (NOT `mnemosyne` — the audit confirmed this is the actual PyPI name; the bare name `mnemosyne` doesn't resolve). If your install fails, double-check the user's repo at `https://github.com/rakaarwaky/mnemosyne` for the canonical pip-installable name in their README.

**Failure protocol:** if `pip install mnemosyne-memory` fails (package renamed, taken down, or never published), write a blocked-handoff and skip. Don't `git clone` the repo into `node_modules` / `site-packages`.

### 5.2 `core/memory/mnemosyne_recall.py` (NEW)

```python
"""Mnemosyne-backed recall layer for Hermes3D agents.

CRITICAL: This is a RECALL layer, NOT a source of truth.

The evidence ledger at var/proofs/...ndjson remains canonical. Mnemosyne
stores NON-canonical hints — printer quirks observed, agent failure
patterns, reinforcement signals. Decisions cite recall hints; they don't
authoritatively rely on them.

If Mnemosyne is unavailable (offline DB, package import error), the
agents continue with deterministic logic — degraded but functional.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

LOG = logging.getLogger(__name__)


@dataclass
class RecallHint:
    hint_id: str
    kind: str
    text: str
    relevance: float
    metadata: dict = field(default_factory=dict)


class MnemosyneRecall:
    """Soft-import wrapper. Methods no-op if Mnemosyne is unavailable."""

    KINDS = frozenset({
        "printer_quirk",
        "material_quirk",
        "scheduling_pref",
        "user_preference",
        "failure_pattern",
        "parameter_override",
    })

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db = None
        try:
            import mnemosyne_memory  # type: ignore[import-not-found]
        except ImportError:
            LOG.info("mnemosyne-memory not installed; recall layer disabled")
            return
        try:
            self._db = mnemosyne_memory.open(
                str(db_path or Path.home() / ".hermes3d" / "mnemosyne.db")
            )
        except Exception as exc:
            LOG.warning("Mnemosyne open failed: %s; recall layer disabled", exc)

    def remember(self, kind: str, text: str, **metadata) -> Optional[str]:
        if self._db is None or kind not in self.KINDS:
            return None
        try:
            return self._db.remember(kind=kind, text=text, **metadata)
        except Exception as exc:
            LOG.warning("Mnemosyne remember failed: %s", exc)
            return None

    def search(
        self, query: str, kind: Optional[str] = None, limit: int = 5
    ) -> list[RecallHint]:
        if self._db is None:
            return []
        try:
            raw = self._db.search(query=query, kind=kind, limit=limit)
            return [
                RecallHint(
                    hint_id=r["id"],
                    kind=r["kind"],
                    text=r["text"],
                    relevance=r.get("score", 0.0),
                    metadata=r.get("metadata", {}),
                )
                for r in raw
            ]
        except Exception as exc:
            LOG.warning("Mnemosyne search failed: %s", exc)
            return []

    def forget(self, hint_id: str) -> None:
        if self._db is None:
            return
        try:
            self._db.forget(hint_id)
        except Exception as exc:
            LOG.warning("Mnemosyne forget failed: %s", exc)


def default_recall() -> MnemosyneRecall:
    """Singleton-ish factory; agents call this rather than constructing directly."""
    return MnemosyneRecall()
```

### 5.3 Wire into orchestrator + dispatcher

**`core/agents/orchestrator.py`** — at orchestrator init, store a `MnemosyneRecall` instance. Pass it to dispatcher / mesh-repair / preflight as an optional kwarg (`recall: MnemosyneRecall | None = None`). Default behavior unchanged when recall is `None`.

**`core/agents/dispatcher.py`** — in the scoring function, after the deterministic score, call `recall.search(query=...)` with a query like `"printer={printer_id} material={material} quality={quality}"`. If hints exist, blend their reinforcement into the score (small weight — e.g., +0.05 for confirmed-good, -0.10 for confirmed-failure). DO NOT let recall hints alone flip the verdict; the deterministic score must dominate.

After a successful print, the post-print agent should `recall.remember(kind="parameter_override", text="prusa-mk4-02 + PLA + normal-quality + flow=98% → success", ...)`.

### 5.4 Tests (`test_mnemosyne_recall.py`)

```python
def test_remember_search_round_trip(tmp_path):
    recall = MnemosyneRecall(db_path=tmp_path / "test.db")
    if recall._db is None:
        pytest.skip("mnemosyne-memory not installed")
    hint_id = recall.remember(
        kind="printer_quirk",
        text="prusa-mk4-02 needs Z-offset -0.05 with PEI",
    )
    hits = recall.search("prusa-mk4-02", kind="printer_quirk")
    assert any(h.text.startswith("prusa-mk4-02") for h in hits)


def test_recall_unavailable_silent_degradation(monkeypatch):
    monkeypatch.setattr(
        "hermes3d.core.memory.mnemosyne_recall.MnemosyneRecall._db", None
    )
    recall = MnemosyneRecall()
    assert recall.remember("printer_quirk", "test") is None
    assert recall.search("anything") == []


def test_recall_hints_do_not_appear_in_evidence_ledger(tmp_path):
    """Recall is NOT canonical. The ledger must be untouched."""
    # This test should grep var/proofs/*.ndjson before + after a recall.remember()
    # call and confirm zero new ledger entries.
    ...
```

### 5.5 ADR

**`02_architecture/adr/ADR-016-mnemosyne-recall-layer.md`** — 8 sections per the corrected ADR template (or ADR-017 if -016 collides). Decision: Mnemosyne is a recall layer, NOT a source of truth. Evidence ledger remains canonical. Falls back to deterministic logic when unavailable.

### 5.6 Honesty ledger

**`HONESTY_LEDGER.md`** — append rows:

- `core.memory.mnemosyne_recall` — REAL when `mnemosyne-memory` installed; DEGRADED-OK when not. Recall layer, not source of truth.

---

## 6. Tests + gates

```text
hermes_run_gate gateId=git-status      cwd=.
hermes_run_gate gateId=git-diff-check  cwd=.
```

Local:
- `pip install -e ".[all]"` succeeds (with `mnemosyne-memory` added)
- `pytest -q 04_testing/pytest/` — 670+ existing + 3 new, all pass
- `pytest -q 04_testing/pytest/ -k mnemosyne` — 3 new tests
- Soft-import smoke: temporarily uninstall `mnemosyne-memory`; `pytest -k mnemosyne` should pass via skip; orchestrator should still init.

---

## 7. PR + close-out

```bash
git push -u origin feat/cp-hermes3d-mnemosyne-recall
gh pr create --base develop \
  --title "feat(memory): Mnemosyne recall layer (Task 4b)" \
  --body "[Hermes evidence chain: PASS; Task: CP-HERMES3D-MNEMOSYNE-RECALL; Gate run via hermes_run_gate]"
```

Close-out per standard pattern.

---

## 8. Hard rules

- DO NOT make Mnemosyne the source of truth for ANY decision — recall layer ONLY
- DO NOT commit the SQLite DB file (it's user-data, gitignored at `var/`)
- DO NOT swallow exceptions from Mnemosyne silently — LOG.warning with context
- DO NOT add the package as a runtime dependency without `try/except ImportError` guard
- DO NOT touch any file outside the §4 lock list

## 9. Failure protocol

If `mnemosyne-memory` fails to install (renamed package, BEAM-only, taken down), the soft-import pattern in §5.2 already handles it gracefully — the recall layer is disabled, agents continue with deterministic logic. Skip the dependency add in §5.1, but ship the wrapper module + tests anyway. The architect can wire in a real implementation later.

If integration with the dispatcher introduces a regression in existing tests, prefer keeping the dispatcher behavior identical when `recall is None` — that's the safe path.
