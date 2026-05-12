"""W21 MVP-3 — unit tests for ``hermes3d.services.persona_executor``.

Mission: pin the executor's classification + transition contract WITHOUT
calling the real LLM. The LLM call is monkeypatched to a deterministic
fake so we can assert on the resulting markdown body, the proof events,
and the queue lifecycle transitions.

These tests cover the bounded inner contract; the integration test
hits the FastAPI route + queue_bridge filesystem layer end-to-end.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hermes3d.services import persona_executor, queue_bridge

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed_task(
    root: Path,
    task_id: str,
    *,
    state: str = "claimed",
    target_owner_pattern: str = "factory-operator",
    priority: int = 80,
    handoff_path: str | None = None,
    claimed_by: str | None = "hermes/factory-operator",
    title: str | None = None,
    summary: str = "",
) -> Path:
    state_dir = root / ".hermes3d_orchestrator" / "tasks" / state
    state_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "task_schema_version": 1,
        "task_id": task_id,
        "title": title or f"test {task_id}",
        "summary": summary or f"summary for {task_id}",
        "target_owner_pattern": target_owner_pattern,
        "priority": priority,
        "claimed_by": claimed_by,
        "claimed_utc": "2026-05-12T00:00:00.000000Z" if claimed_by else None,
        "heartbeat_utc": "2026-05-12T00:00:00.000000Z" if claimed_by else None,
        "done_utc": None,
        "blocked_reason": None,
        "handoff_path": handoff_path,
    }
    path = state_dir / f"{task_id}.json"
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# classify_task
# ---------------------------------------------------------------------------


def test_classify_audit_task_with_md_handoff(tmp_path: Path) -> None:
    """Tasks named *_AUDIT_*.md classify as audit."""
    _seed_task(
        tmp_path,
        "W21-A99-TEST-AUDIT-2026-05-12",
        handoff_path="03_implementation/docs/handoffs/W21_A99_TEST_AUDIT_2026-05-12.md",
    )
    snaps = queue_bridge.list_tasks(tmp_path, "claimed")
    assert snaps and persona_executor.classify_task(snaps[0]) == "audit"


def test_classify_plan_task_is_audit_class(tmp_path: Path) -> None:
    _seed_task(
        tmp_path,
        "W21-A8-GEN3D-MODEL-INSTALL-EXECUTION-PLAN-2026-05-12",
        handoff_path="03_implementation/docs/handoffs/W21_A8_PLAN.md",
    )
    snaps = queue_bridge.list_tasks(tmp_path, "claimed")
    assert snaps and persona_executor.classify_task(snaps[0]) == "audit"


def test_classify_unknown_when_no_md_handoff(tmp_path: Path) -> None:
    _seed_task(
        tmp_path,
        "W21-A99-TEST-AUDIT-2026-05-12",
        handoff_path="03_implementation/var/output.stl",
    )
    snaps = queue_bridge.list_tasks(tmp_path, "claimed")
    assert snaps and persona_executor.classify_task(snaps[0]) == "unknown"


def test_classify_unknown_when_taskid_lacks_class_marker(tmp_path: Path) -> None:
    _seed_task(
        tmp_path,
        "W21-A99-BUILD-FEATURE",
        handoff_path="03_implementation/docs/handoffs/W21_A99_BUILD.md",
    )
    snaps = queue_bridge.list_tasks(tmp_path, "claimed")
    assert snaps and persona_executor.classify_task(snaps[0]) == "unknown"


# ---------------------------------------------------------------------------
# execute_one — unknown-class path: must move task to blocked/
# ---------------------------------------------------------------------------


def test_unknown_class_moves_task_to_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    _seed_task(
        tmp_path,
        "W21-A99-BUILD-FEATURE",
        handoff_path="03_implementation/docs/handoffs/W21_A99_BUILD.md",
    )
    snap = queue_bridge.list_tasks(tmp_path, "claimed")[0]
    result = persona_executor.execute_one(snap, tmp_path)
    assert result["outcome"] == "blocked"
    assert result["reason"].startswith("no_automated_executor_for_task_class")
    # File moved from claimed/ to blocked/
    assert (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "blocked" / f"{snap.task_id}.json"
    ).exists()
    assert not (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "claimed" / f"{snap.task_id}.json"
    ).exists()


# ---------------------------------------------------------------------------
# execute_one — audit-class success path: must write handoff + move to done/
# ---------------------------------------------------------------------------


def test_audit_class_writes_handoff_and_marks_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Monkeypatches the LLM caller so the test is hermetic."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))

    handoff_rel = "03_implementation/docs/handoffs/W21_A99_TEST_AUDIT_2026-05-12.md"
    _seed_task(
        tmp_path,
        "W21-A99-TEST-AUDIT-2026-05-12",
        handoff_path=handoff_rel,
        title="Test Audit",
        summary="Verify the executor produces a real handoff file.",
    )
    snap = queue_bridge.list_tasks(tmp_path, "claimed")[0]

    # Patch the LLM call to a deterministic stub so the test doesn't hit
    # MiniMax (and so the test passes on a machine without API keys).
    fake_body = "# Test Audit\n\nVerdict: stubbed for unit test.\nNo external calls made."
    fake_metadata = {"model": "stub-llm", "tokens_in": 100, "tokens_out": 50}

    def _fake_generate(task, persona):  # noqa: ANN001
        return fake_body, fake_metadata

    monkeypatch.setattr(persona_executor, "_generate_audit_markdown", _fake_generate)

    result = persona_executor.execute_one(snap, tmp_path)

    assert result["outcome"] == "done"
    assert result["reason"] == "audit_handoff_generated"
    assert result["class"] == "audit"
    assert result["handoff"] is not None

    # Handoff markdown exists and contains BOTH the MVP-3 header + the
    # generated body.
    written = Path(result["handoff"])
    assert written.exists()
    content = written.read_text(encoding="utf-8")
    assert "MVP-3 attestation" in content
    assert "operator review REQUIRED" in content
    assert "stub-llm" in content  # metadata exposed in header
    assert fake_body in content  # LLM body included

    # Task moved from claimed/ to done/.
    assert (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "done" / f"{snap.task_id}.json"
    ).exists()


def test_audit_class_llm_failure_routes_to_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the LLM call returns None (failure), task goes to blocked/."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    _seed_task(
        tmp_path,
        "W21-A99-LLM-FAIL-AUDIT-2026-05-12",
        handoff_path="03_implementation/docs/handoffs/W21_A99_LLM_FAIL_AUDIT.md",
    )
    snap = queue_bridge.list_tasks(tmp_path, "claimed")[0]

    monkeypatch.setattr(persona_executor, "_generate_audit_markdown", lambda t, p: None)

    result = persona_executor.execute_one(snap, tmp_path)
    assert result["outcome"] == "blocked"
    assert result["reason"] == "llm_generation_failed_or_unavailable"
    assert (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "blocked" / f"{snap.task_id}.json"
    ).exists()


# ---------------------------------------------------------------------------
# execute_claimed_tasks — multi-task, budget, persona filter
# ---------------------------------------------------------------------------


def test_executor_disabled_env_var_makes_executor_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("HERMES3D_PERSONA_EXECUTOR_DISABLED", "1")
    _seed_task(tmp_path, "W21-A99-TEST-AUDIT", handoff_path="x.md")
    results = persona_executor.execute_claimed_tasks(workspace_root=tmp_path)
    assert results == []


def test_executor_respects_max_per_tick(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("HERMES3D_PERSONA_EXEC_MAX_PER_TICK", "1")
    monkeypatch.setattr(
        persona_executor,
        "_generate_audit_markdown",
        lambda t, p: ("# stub", {"model": "stub", "tokens_in": 1, "tokens_out": 1}),
    )
    for i in range(3):
        _seed_task(
            tmp_path,
            f"W21-A{i:02d}-MULTI-AUDIT-2026-05-12",
            handoff_path=f"03_implementation/docs/handoffs/W21_A{i:02d}_AUDIT.md",
            priority=100 - i,
        )
    results = persona_executor.execute_claimed_tasks(workspace_root=tmp_path)
    assert len(results) == 1  # max=1 enforced


def test_executor_skips_tasks_not_owned_by_hermes_persona(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tasks claimed by external actors (no hermes/ prefix) are skipped."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        persona_executor,
        "_generate_audit_markdown",
        lambda t, p: ("# stub", {"model": "stub", "tokens_in": 1, "tokens_out": 1}),
    )
    # Two tasks: one owned by hermes/<persona>, one by an external actor.
    _seed_task(
        tmp_path,
        "W21-A1-OURS-AUDIT",
        handoff_path="03_implementation/docs/handoffs/W21_A1_OURS_AUDIT.md",
        claimed_by="hermes/factory-operator",
    )
    _seed_task(
        tmp_path,
        "W21-A2-THEIRS-AUDIT",
        handoff_path="03_implementation/docs/handoffs/W21_A2_THEIRS_AUDIT.md",
        claimed_by="codex-some-other-actor",
    )
    results = persona_executor.execute_claimed_tasks(workspace_root=tmp_path)
    assert len(results) == 1
    assert results[0]["task_id"] == "W21-A1-OURS-AUDIT"
