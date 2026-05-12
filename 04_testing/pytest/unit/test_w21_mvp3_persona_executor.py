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
    # Stub body is ~500 chars of clean markdown so it passes the quality
    # gate (>= 400 chars + no surviving think tags + few boilerplate).
    fake_body = (
        "# Test Audit\n\n"
        "**Verdict:** Hermes3D backend at /api/agents/health responds 200 with "
        "factory-operator persona registered and active. No printer hardware actions performed.\n\n"
        "## Findings\n\n"
        "1. `/api/agents/queue/status` returned 8 claimed tasks at probe time.\n"
        "2. Workspace root `G:/Github/Hermes3D` confirmed via env var.\n"
        "3. proof_events table at var/hermes3d.db contains live rows.\n\n"
        "## Recommended next actions\n\n"
        "- Operator: verify each row by file path.\n"
        "- Operator: re-run after next CI cycle.\n"
    )
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
    # LLM body included (substring checks; sanitizer trims trailing whitespace
    # so full-string equality would be flakey).
    assert "Verdict:" in content
    assert "/api/agents/queue/status" in content
    assert "Recommended next actions" in content

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
# Sanitizer: closed/unclosed <think>, whole-doc markdown fence, blank-line collapse
# ---------------------------------------------------------------------------


def test_sanitize_strips_closed_think_block() -> None:
    raw = "<think>let me reason</think>\n# Real Doc\n\nbody"
    out = persona_executor._sanitize_llm_output(raw)
    assert "<think>" not in out
    assert "let me reason" not in out
    assert "# Real Doc" in out


def test_sanitize_drops_unclosed_think_to_eof() -> None:
    raw = "# Header\n\nReal body.\n\n<think>\nReasoning interrupted by token limit"
    out = persona_executor._sanitize_llm_output(raw)
    assert "<think>" not in out
    assert "Reasoning interrupted" not in out
    assert "# Header" in out
    assert "Real body." in out


def test_sanitize_unwraps_whole_doc_markdown_fence() -> None:
    raw = "```markdown\n# Real Title\n\nReal content here.\n```"
    out = persona_executor._sanitize_llm_output(raw)
    assert "```markdown" not in out
    assert out.startswith("# Real Title")
    assert "Real content here." in out


def test_sanitize_unwraps_bare_triple_fence() -> None:
    raw = "```\n# Real Title\n\nbody body body\n```"
    out = persona_executor._sanitize_llm_output(raw)
    assert out.strip().startswith("# Real Title")
    assert "body body body" in out


def test_sanitize_collapses_excess_blank_lines() -> None:
    raw = "# A\n\n\n\n\nbody"
    out = persona_executor._sanitize_llm_output(raw)
    # 3+ blank lines collapsed to 2.
    assert "\n\n\n" not in out


def test_sanitize_no_tags_passes_through() -> None:
    raw = "# Clean Audit\n\nNo reasoning leakage."
    assert persona_executor._sanitize_llm_output(raw) == raw.strip()


# ---------------------------------------------------------------------------
# Quality gate: reject empty, too-short, surviving think, boilerplate density
# ---------------------------------------------------------------------------


def test_quality_gate_passes_substantial_clean_doc() -> None:
    body = (
        "# Real Audit\n\n"
        "**Verdict:** /api/agents/health returned 200 with the factory-operator "
        "persona active. Workspace root probed at G:/Github/Hermes3D and confirmed "
        "via the HERMES3D_WORKSPACE_ROOT env var.\n\n"
        "## Findings\n\n"
        "1. /api/agents/queue/status reported 8 claimed tasks across persona pool.\n"
        "2. proof_events SQLite table at var/hermes3d.db received the live row.\n"
        "3. No printer hardware action was taken at any point during the audit.\n"
        "4. queue_bridge.list_tasks returned consistent entries on two reads.\n\n"
        "## Recommended next actions\n\n"
        "- Operator: review per-task handoff content and merge to develop.\n"
        "- Operator: re-run after the next CI cycle to confirm idempotence.\n"
    )
    ok, reason = persona_executor._passes_quality_gate(body)
    assert ok, reason


def test_quality_gate_rejects_empty() -> None:
    ok, reason = persona_executor._passes_quality_gate("")
    assert not ok
    assert "empty" in reason


def test_quality_gate_rejects_too_short() -> None:
    ok, reason = persona_executor._passes_quality_gate("# tiny\n\nbody")
    assert not ok
    assert "too_short" in reason


def test_quality_gate_rejects_surviving_think_tag() -> None:
    body = "x" * 500 + "\n\n<think>sanitizer bypass attempt</think>"
    ok, reason = persona_executor._passes_quality_gate(body)
    assert not ok
    assert "think_tag_survived" in reason


def test_quality_gate_rejects_boilerplate_density() -> None:
    body = (
        "# Mostly Useless Audit\n\n"
        "Verdict: not measured.\n"
        "Scope: not measured.\n"
        "Findings: operator must verify these.\n"
        "1. not measured.\n"
        "2. not measured.\n"
        "3. operator must verify.\n" + "additional padding " * 30
    )
    ok, reason = persona_executor._passes_quality_gate(body)
    assert not ok
    assert "boilerplate" in reason


def test_quality_gate_rejects_surviving_whole_doc_markdown_fence() -> None:
    body = "```markdown\n# Doc\n\nstuff " * 40
    ok, reason = persona_executor._passes_quality_gate(body)
    assert not ok
    assert "whole_document_markdown_fence" in reason


def test_quality_gate_rejects_hallucinated_vue_path() -> None:
    """Vue isn't used in this codebase. A Vue file mention is a
    hallucination (LLM invented framework) and must be rejected."""
    body = (
        "# Audit Draft\n\n"
        "Verdict: backend probed.\n\n"
        "## Findings\n\n"
        "1. The polling loop in `src/components/AgentTaskList.vue` line 45 "
        "uses a 30 s interval and never receives push updates from "
        "/api/events. This is a legitimate-sounding but invented citation.\n"
        "2. Cache invalidation needs attention.\n"
        "3. Refresh buttons trigger full reloads.\n\n"
        "## Recommended next actions\n\n"
        "- Operator: investigate.\n"
        "- Operator: add WebSocket push.\n"
    )
    ok, reason = persona_executor._passes_quality_gate(body)
    assert not ok
    assert "hallucinated_framework" in reason
    assert ".vue" in reason


def test_quality_gate_rejects_hallucinated_django() -> None:
    body = (
        "# Audit\n\nVerdict: Django backend at /api/agents/health returns 200.\n\n"
        "## Findings\n\n1. Concrete finding A.\n2. Concrete finding B.\n3. Concrete finding C.\n\n"
        "## Recommended actions\n\n- Operator: review.\n- Operator: act.\n"
        + "padding-line content here. "
        * 20
    )
    ok, reason = persona_executor._passes_quality_gate(body)
    assert not ok
    assert "hallucinated_framework" in reason


def test_quality_gate_accepts_legitimate_fastapi_react_mentions() -> None:
    """FastAPI + React are the REAL stack and must NOT trip the hallucination
    tripwire."""
    body = (
        "# Audit\n\n"
        "Verdict: the FastAPI backend at /api/agents/health responds 200 and "
        "the React UI under 03_implementation/ui/src renders the dashboard.\n\n"
        "## Findings\n\n"
        "1. `/api/agents/queue/status` reports counts consistently.\n"
        "2. `services/persona_executor` is wired into queue_poller tick.\n"
        "3. `var/hermes3d.db` is the canonical SQLite path.\n\n"
        "## Recommended next actions\n\n"
        "- Operator: review the proof_events table.\n"
        "- Operator: re-run after merge.\n"
    )
    ok, reason = persona_executor._passes_quality_gate(body)
    assert ok, reason


# ---------------------------------------------------------------------------
# Preserve-existing handoff: if file exists with substantial content,
# executor must NOT overwrite — must mark task done with the preserve reason.
# ---------------------------------------------------------------------------


def test_existing_substantial_handoff_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the target handoff_path already has >= 200 bytes of content,
    the executor must NOT clobber it — must mark task done with reason
    'preserved_existing_handoff' and emit a matching proof event."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    handoff_rel = "03_implementation/docs/handoffs/W21_A99_HUMAN_AUDIT.md"
    handoff_abs = tmp_path / handoff_rel
    handoff_abs.parent.mkdir(parents=True, exist_ok=True)
    # Seed a "human-written" handoff with substantial real content.
    human_content = (
        "# Human-written audit (DO NOT OVERWRITE)\n\n"
        "This audit was hand-written by an operator. The W21-MVP-3 "
        "executor MUST preserve this file rather than replace it with an "
        "LLM draft. "
    ) * 4
    handoff_abs.write_text(human_content, encoding="utf-8")
    bytes_before = handoff_abs.stat().st_size
    assert bytes_before >= 200

    _seed_task(
        tmp_path,
        "W21-A99-PRESERVE-AUDIT-2026-05-12",
        handoff_path=handoff_rel,
    )
    snap = queue_bridge.list_tasks(tmp_path, "claimed")[0]

    # Even if the LLM stub returns garbage, the executor must NOT call
    # the LLM (or at minimum must not write). To prove preservation, we
    # make the stub raise loudly if it's invoked.
    def _explode(task, persona):  # noqa: ANN001
        raise AssertionError("LLM should not be invoked when preserving existing handoff")

    monkeypatch.setattr(persona_executor, "_generate_audit_markdown", _explode)

    result = persona_executor.execute_one(snap, tmp_path)
    assert result["outcome"] == "done"
    assert result["reason"] == "preserved_existing_handoff"
    # File content was NOT modified.
    assert handoff_abs.read_text(encoding="utf-8") == human_content
    # Task moved to done/.
    assert (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "done" / f"{snap.task_id}.json"
    ).exists()


def test_tiny_stub_handoff_is_overwritable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A trivially-tiny existing handoff (< 200 bytes) is NOT considered
    substantial; the executor MAY overwrite it with a generated draft."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    handoff_rel = "03_implementation/docs/handoffs/W21_A99_TINY.md"
    handoff_abs = tmp_path / handoff_rel
    handoff_abs.parent.mkdir(parents=True, exist_ok=True)
    handoff_abs.write_text("# stub", encoding="utf-8")  # 6 bytes
    # task_id must end with `-AUDIT-<date>` so the classifier matches.
    _seed_task(tmp_path, "W21-A99-TINY-STUB-AUDIT-2026-05-12", handoff_path=handoff_rel)
    snap = queue_bridge.list_tasks(tmp_path, "claimed")[0]

    fake_body = (
        "# Generated\n\n## Findings\n\n- /api/agents/health 200\n- workspace_root probed\n"
        + "additional concrete claim line " * 20
    )
    monkeypatch.setattr(
        persona_executor,
        "_generate_audit_markdown",
        lambda t, p: (fake_body, {"model": "stub", "tokens_in": 1, "tokens_out": 1}),
    )
    result = persona_executor.execute_one(snap, tmp_path)
    assert result["outcome"] == "done"
    assert result["reason"] == "audit_handoff_generated"
    assert handoff_abs.read_text(encoding="utf-8") != "# stub"


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


def test_strip_think_blocks_removes_closed_think_tags() -> None:
    """Closed ``<think>...</think>`` blocks are stripped before write."""
    raw = (
        "<think>\nThe user wants me to produce X. Let me think...\n</think>\n"
        "# Real Answer\n\nThis is the actual audit content."
    )
    stripped = persona_executor._strip_think_blocks(raw)
    assert "<think>" not in stripped
    assert "Let me think" not in stripped
    assert "# Real Answer" in stripped
    assert "actual audit content" in stripped


def test_strip_think_blocks_drops_unclosed_think_when_truncated() -> None:
    """When token budget truncates a ``<think>`` block, the entire
    open-tag-to-EOF gets dropped — those tokens are useless to operators."""
    raw = (
        "# Real Header\n\nSome content.\n\n<think>\n"
        "Mid-reasoning, the model ran out of tokens here."
    )
    stripped = persona_executor._strip_think_blocks(raw)
    assert "<think>" not in stripped
    assert "Mid-reasoning" not in stripped
    assert "# Real Header" in stripped
    assert "Some content." in stripped


def test_strip_think_blocks_handles_no_think_tags() -> None:
    """Markdown without ``<think>`` blocks is returned unchanged (modulo
    leading/trailing whitespace)."""
    raw = "# Clean Audit\n\nNo reasoning leakage here.\n"
    stripped = persona_executor._strip_think_blocks(raw)
    assert stripped == raw.strip()


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
