"""W21 MVP-3 — integration test for the persona executor HTTP surface.

Mission: prove the operator can drive a claimed task to DONE (or BLOCKED)
via ``POST /api/agents/queue/execute-now`` and observe the resulting
handoff markdown on disk + the queue lifecycle transition + the proof
event row. The LLM is patched to a deterministic stub so tests are
hermetic.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Spin up a fresh FastAPI app rooted at tmp_path."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("HERMES3D_QUEUE_POLLER_DISABLED", "1")
    db_path = tmp_path / "hermes3d.db"
    for mod_name in list(sys.modules):
        if mod_name.startswith("hermes3d.api.app") or mod_name.startswith("hermes3d.api.routes"):
            sys.modules.pop(mod_name, None)
    sys.modules.pop("hermes3d.config.env_loader", None)
    sys.modules.pop("hermes3d.services.queue_bridge", None)
    sys.modules.pop("hermes3d.services.queue_poller", None)
    sys.modules.pop("hermes3d.services.persona_executor", None)
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    # Patch the LLM caller globally so the integration test stays hermetic.
    persona_executor_mod = importlib.import_module("hermes3d.services.persona_executor")
    fake_md = "# Integration Test Audit\n\nVerdict: stubbed for integration test.\n"
    fake_meta = {"model": "stub-llm", "tokens_in": 100, "tokens_out": 30}
    monkeypatch.setattr(
        persona_executor_mod, "_generate_audit_markdown", lambda t, p: (fake_md, fake_meta)
    )

    app_mod = importlib.import_module("hermes3d.api.app")
    return TestClient(app_mod.create_gui_app())


def _seed_task(
    root: Path,
    task_id: str,
    *,
    state: str = "claimed",
    handoff_path: str | None = None,
    claimed_by: str | None = "hermes/factory-operator",
    target_owner_pattern: str = "factory-operator",
) -> None:
    state_dir = root / ".hermes3d_orchestrator" / "tasks" / state
    state_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "task_schema_version": 1,
        "task_id": task_id,
        "title": f"Integration test {task_id}",
        "summary": f"Integration test for {task_id}",
        "target_owner_pattern": target_owner_pattern,
        "priority": 80,
        "claimed_by": claimed_by,
        "claimed_utc": "2026-05-12T00:00:00.000000Z",
        "heartbeat_utc": "2026-05-12T00:00:00.000000Z",
        "done_utc": None,
        "blocked_reason": None,
        "handoff_path": handoff_path,
    }
    (state_dir / f"{task_id}.json").write_text(json.dumps(body, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# /api/agents/queue/execute-now — single audit task path to done
# ---------------------------------------------------------------------------


def test_execute_now_drives_audit_task_to_done(client: TestClient, tmp_path: Path) -> None:
    """E2E: claimed audit task → execute-now → handoff written on disk → done/."""
    handoff_rel = "03_implementation/docs/handoffs/W21_A99_E2E_AUDIT_2026-05-12.md"
    _seed_task(tmp_path, "W21-A99-E2E-AUDIT-2026-05-12", handoff_path=handoff_rel)

    # Confirm baseline.
    pre = client.get("/api/agents/queue/status").json()
    assert pre["counts"]["claimed"] == 1
    assert pre["counts"]["done"] == 0

    # Trigger the executor.
    resp = client.post("/api/agents/queue/execute-now")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted"] is True
    assert body["counts"]["done"] == 1
    assert body["counts"]["blocked"] == 0
    assert body["results"][0]["outcome"] == "done"
    assert body["results"][0]["reason"] == "audit_handoff_generated"

    # Handoff exists on disk.
    written = Path(body["results"][0]["handoff"])
    assert written.exists()
    content = written.read_text(encoding="utf-8")
    assert "MVP-3 attestation" in content
    assert "operator review REQUIRED" in content

    # Queue lifecycle: claimed → done.
    post = client.get("/api/agents/queue/status").json()
    assert post["counts"]["claimed"] == 0
    assert post["counts"]["done"] == 1

    # Filesystem evidence: file moved.
    assert (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "done" / "W21-A99-E2E-AUDIT-2026-05-12.json"
    ).exists()
    assert not (
        tmp_path
        / ".hermes3d_orchestrator"
        / "tasks"
        / "claimed"
        / "W21-A99-E2E-AUDIT-2026-05-12.json"
    ).exists()


# ---------------------------------------------------------------------------
# /api/agents/queue/execute-now — unknown class path to blocked
# ---------------------------------------------------------------------------


def test_execute_now_moves_unknown_class_to_blocked(client: TestClient, tmp_path: Path) -> None:
    """A claimed task with no executor → moves to blocked/ with reason."""
    _seed_task(
        tmp_path,
        "W21-A99-BUILD-FEATURE",
        handoff_path="03_implementation/docs/handoffs/W21_A99_BUILD.md",
    )
    resp = client.post("/api/agents/queue/execute-now")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["counts"]["done"] == 0
    assert body["counts"]["blocked"] == 1
    assert body["results"][0]["outcome"] == "blocked"
    assert body["results"][0]["reason"].startswith("no_automated_executor_for_task_class")
    # Filesystem evidence: file moved to blocked/.
    assert (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "blocked" / "W21-A99-BUILD-FEATURE.json"
    ).exists()


# ---------------------------------------------------------------------------
# Proof event persistence
# ---------------------------------------------------------------------------


def test_execute_now_emits_proof_event(client: TestClient, tmp_path: Path) -> None:
    """A successful execute-now run must write a row to the proof_events
    table (`persona_executor.task.done` event type)."""
    import sqlite3

    handoff_rel = "03_implementation/docs/handoffs/W21_A99_PROOF_TEST_AUDIT_2026-05-12.md"
    _seed_task(tmp_path, "W21-A99-PROOF-TEST-AUDIT-2026-05-12", handoff_path=handoff_rel)
    resp = client.post("/api/agents/queue/execute-now")
    assert resp.status_code == 200

    db_path = tmp_path / "hermes3d.db"
    assert db_path.exists()
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        rows = cur.execute(
            "SELECT event_type, source_agent FROM proof_events WHERE event_type LIKE ?",
            ("persona_executor.%",),
        ).fetchall()
    assert any(r[0] == "persona_executor.task.done" for r in rows), (
        f"expected a persona_executor.task.done event in proof_events; got {rows!r}"
    )


# ---------------------------------------------------------------------------
# Mixed-batch: 1 audit + 1 unknown in same execute-now call
# ---------------------------------------------------------------------------


def test_execute_now_mixed_batch_done_plus_blocked(client: TestClient, tmp_path: Path) -> None:
    """Same call returns both done and blocked outcomes correctly."""
    _seed_task(
        tmp_path,
        "W21-A1-MIXED-AUDIT-2026-05-12",
        handoff_path="03_implementation/docs/handoffs/W21_A1_MIXED_AUDIT.md",
    )
    _seed_task(
        tmp_path,
        "W21-A2-MIXED-BUILD",
        handoff_path="03_implementation/docs/handoffs/W21_A2_MIXED_BUILD.md",
    )
    resp = client.post("/api/agents/queue/execute-now")
    body = resp.json()
    assert body["counts"]["done"] == 1
    assert body["counts"]["blocked"] == 1
    final = client.get("/api/agents/queue/status").json()
    assert final["counts"]["done"] == 1
    assert final["counts"]["blocked"] == 1
    assert final["counts"]["claimed"] == 0
