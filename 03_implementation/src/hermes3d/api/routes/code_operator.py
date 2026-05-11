"""Hermes Agent code-operation APIs for source-backed programming work."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from hermes3d.api.routes._common import rows
from hermes3d.services import code_history, recovery_controller

router = APIRouter(prefix="/api/code-operator", tags=["code-operator"])
CODE_OPERATOR_ACTOR = "hermes-agent"


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SnapshotRequest(StrictBody):
    relative_path: str
    action_id: str | None = None
    reason: str | None = None


class RestoreRequest(StrictBody):
    relative_path: str
    snapshot_id: str
    task_id: str
    reason: str | None = None


class SnapshotQuery(StrictBody):
    relative_path: str
    limit: int = Field(default=100, ge=1, le=500)


class SearchRequest(StrictBody):
    pattern: str = Field(min_length=1, max_length=160)
    root: str = "."
    max_results: int = Field(default=100, ge=1, le=200)


class ReadFileRequest(StrictBody):
    relative_path: str
    start_line: int = Field(default=1, ge=1)
    line_count: int = Field(default=120, ge=1, le=240)


class PatchProposalRequest(StrictBody):
    relative_path: str
    proposed_text: str = Field(max_length=1024 * 1024)
    base_sha256: str | None = None
    reason: str | None = None


class PatchApplyRequest(StrictBody):
    proposal_id: str
    task_id: str
    reason: str | None = None


class ReviewedPatchApplyRequest(PatchApplyRequest):
    review_proof_ids: list[str] = Field(min_length=1)


class GateRunRequest(StrictBody):
    gate_id: str
    cwd: str | None = None


class GitBranchRequest(StrictBody):
    task_id: str
    branch_name: str
    base_ref: str | None = None
    reason: str = ""


class GitStageRequest(StrictBody):
    task_id: str
    files: list[str] = Field(min_length=1)


class GitCommitRequest(StrictBody):
    task_id: str
    files: list[str] = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4096)
    proof_ids: list[str] = Field(default_factory=list)


class GitPushRequest(StrictBody):
    task_id: str
    remote: str = "origin"


class GitPullRequestRequest(StrictBody):
    task_id: str
    base_ref: str
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(default="", max_length=32000)
    draft: bool = True


class McpTaskClaimRequest(StrictBody):
    task_id: str
    title: str = ""
    files: list[str] = Field(default_factory=list)
    reason: str = ""
    role: str = "agent"


class McpFileLockRequest(StrictBody):
    files: list[str] = Field(min_length=1)
    task_id: str
    reason: str = ""
    role: str = "agent"
    ttl_minutes: int = Field(default=90, ge=5, le=720)


class McpHeartbeatRequest(StrictBody):
    task_id: str


class McpReleaseFilesRequest(StrictBody):
    files: list[str] = Field(min_length=1)
    note: str = ""


class McpReleaseTaskRequest(StrictBody):
    task_id: str
    note: str = ""


class McpEvidenceRequest(StrictBody):
    task_id: str
    kind: str = "proof"
    summary: str = Field(min_length=1, max_length=400)
    data: dict[str, Any] = Field(default_factory=dict)


class ProviderTeamAssignmentRequest(StrictBody):
    team_id: str
    task_id: str
    title: str = Field(min_length=1, max_length=180)
    files: list[str] = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=1600)
    target_branch: str | None = None
    review_required: bool = True


class ProviderTeamReviewRequest(StrictBody):
    task_id: str
    summary: str = Field(min_length=1, max_length=1200)
    files: list[str] = Field(min_length=1)
    proof_ids: list[str] = Field(min_length=1)
    reviewer_team_id: str = "deepseek-reviewers"


class ProviderCodingPassRequest(StrictBody):
    team_id: str = "minimax-builders"
    task_id: str
    title: str = Field(min_length=1, max_length=180)
    files: list[str] = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=2400)
    target_branch: str | None = None


class ProviderReviewPassRequest(StrictBody):
    task_id: str
    summary: str = Field(min_length=1, max_length=2000)
    files: list[str] = Field(min_length=1)
    proof_ids: list[str] = Field(min_length=1)
    reviewer_team_id: str = "deepseek-reviewers"


class ProviderSmokeRequest(StrictBody):
    provider_id: str
    task_id: str


class AgentE2EJobRequest(StrictBody):
    task_id: str
    title: str = Field(min_length=1, max_length=180)
    files: list[str] = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=2400)
    target_branch: str | None = None
    role_chain: list[str] = Field(
        default_factory=lambda: ["finder", "builder", "reviewer", "tester"]
    )
    cli_worker: str | None = None
    release_on_finish: bool = True


class CliRunnerPreflightRequest(StrictBody):
    runner_id: str = Field(min_length=1, max_length=40)
    task_id: str


class CliRunnerRunRequest(StrictBody):
    runner_id: str = Field(min_length=1, max_length=40)
    task_id: str
    title: str = Field(min_length=1, max_length=180)
    files: list[str] = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=2400)
    target_branch: str | None = None


class CliRunnerBoundedTaskRequest(StrictBody):
    """BLK-013 bounded CLI runner task — single-file, no objective string.

    The prompt is fixed server-side (``code_history.BOUNDED_TASK_PROMPT``);
    callers cannot inject. ``files`` must contain exactly one project-relative
    ``.py`` path.
    """

    runner_id: str = Field(min_length=1, max_length=40)
    task_id: str
    title: str = Field(min_length=1, max_length=180)
    files: list[str] = Field(min_length=1, max_length=1)


@router.get("/programming-readiness")
def programming_readiness() -> dict[str, Any]:
    return code_history.programming_readiness()


@router.get("/e2e/readiness")
def agent_e2e_readiness() -> dict[str, Any]:
    return code_history.agent_e2e_readiness()


@router.get("/cli-runners")
def code_cli_runners() -> dict[str, Any]:
    return code_history.code_cli_runners()


@router.get("/sandbox/readiness")
def code_sandbox_readiness() -> dict[str, Any]:
    """Return OpenCode/OpenHands sandbox readiness (I3 spec).

    Fields: opencode_detected, opencode_version, openhands_detected,
    openhands_image, sandbox_network_mode (always "none"), denied_paths, ready.
    """
    return code_history.opencode_openhands_sandbox_readiness()


@router.get("/cli-runners/preflight")
def preflight_code_cli_runner_get(runner_id: str = "opencode") -> dict[str, Any]:
    """Non-mutating dry-run preflight for a CLI runner (GET, no task claim required).

    Runs `<runner> --version` and returns stdout, exit_code, elapsed_ms.
    """
    try:
        return code_history.preflight_code_cli_runner_get(runner_id=runner_id)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/cli-runners/preflight")
def preflight_code_cli_runner(body: CliRunnerPreflightRequest) -> dict[str, Any]:
    try:
        return code_history.preflight_code_cli_runner(
            runner_id=body.runner_id,
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/cli-runners/run")
def run_code_cli_runner(body: CliRunnerRunRequest) -> dict[str, Any]:
    try:
        return code_history.run_code_cli_runner(
            runner_id=body.runner_id,
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            title=body.title,
            files=body.files,
            objective=body.objective,
            target_branch=body.target_branch,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/cli-runners/run-bounded-task")
def run_bounded_code_cli_task(body: CliRunnerBoundedTaskRequest) -> dict[str, Any]:
    """BLK-013 — execute a bounded CLI runner task on the hardened docker sandbox.

    Single fixed prompt, single file, ``--network=none``, stderr returned only as
    sha256, 30s wall-clock timeout, 8 KiB redacted stdout cap.
    """
    try:
        return code_history.run_bounded_code_cli_task(
            runner_id=body.runner_id,
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            title=body.title,
            files=body.files,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/e2e/jobs")
def list_e2e_jobs(limit: int = 100) -> dict[str, Any]:
    try:
        return code_history.list_e2e_jobs(limit=limit)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/e2e/jobs")
def run_agent_e2e_job(body: AgentE2EJobRequest) -> dict[str, Any]:
    try:
        return code_history.run_agent_e2e_job(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            title=body.title,
            files=body.files,
            objective=body.objective,
            target_branch=body.target_branch,
            role_chain=body.role_chain,
            cli_worker=body.cli_worker,
            release_on_finish=body.release_on_finish,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/teams/readiness")
def provider_team_readiness() -> dict[str, Any]:
    return code_history.provider_team_readiness()


@router.post("/providers/smoke")
def provider_smoke(body: ProviderSmokeRequest) -> dict[str, Any]:
    try:
        return code_history.provider_execution_smoke(
            body.provider_id,
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/teams/assign-task")
def provider_team_assign_task(body: ProviderTeamAssignmentRequest) -> dict[str, Any]:
    try:
        return code_history.assign_provider_team_task(
            owner=CODE_OPERATOR_ACTOR,
            team_id=body.team_id,
            task_id=body.task_id,
            title=body.title,
            files=body.files,
            objective=body.objective,
            target_branch=body.target_branch,
            review_required=body.review_required,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/teams/request-review")
def provider_team_request_review(body: ProviderTeamReviewRequest) -> dict[str, Any]:
    try:
        return code_history.request_provider_team_review(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            summary=body.summary,
            files=body.files,
            proof_ids=body.proof_ids,
            reviewer_team_id=body.reviewer_team_id,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/teams/run-coding-pass")
def provider_team_run_coding_pass(body: ProviderCodingPassRequest) -> dict[str, Any]:
    try:
        return code_history.run_provider_team_coding_pass(
            owner=CODE_OPERATOR_ACTOR,
            team_id=body.team_id,
            task_id=body.task_id,
            title=body.title,
            files=body.files,
            objective=body.objective,
            target_branch=body.target_branch,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/teams/run-review-pass")
def provider_team_run_review_pass(body: ProviderReviewPassRequest) -> dict[str, Any]:
    try:
        return code_history.run_provider_team_review_pass(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            summary=body.summary,
            files=body.files,
            proof_ids=body.proof_ids,
            reviewer_team_id=body.reviewer_team_id,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/mcp-locks/readiness")
def mcp_locks_readiness() -> dict[str, Any]:
    return code_history.mcp_lock_readiness()


@router.get("/mcp-locks/state")
def mcp_locks_state() -> dict[str, Any]:
    try:
        return code_history.mcp_lock_state()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/mcp-locks/claim-task")
def mcp_claim_task(body: McpTaskClaimRequest) -> dict[str, Any]:
    try:
        return code_history.claim_mcp_task(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            title=body.title,
            files=body.files,
            reason=body.reason,
            role=body.role,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/mcp-locks/lock-files")
def mcp_lock_files(body: McpFileLockRequest) -> dict[str, Any]:
    try:
        return code_history.lock_mcp_files(
            owner=CODE_OPERATOR_ACTOR,
            files=body.files,
            task_id=body.task_id,
            reason=body.reason,
            role=body.role,
            ttl_minutes=body.ttl_minutes,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/mcp-locks/heartbeat")
def mcp_heartbeat(body: McpHeartbeatRequest) -> dict[str, Any]:
    try:
        return code_history.heartbeat_mcp_task(owner=CODE_OPERATOR_ACTOR, task_id=body.task_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/mcp-locks/release-files")
def mcp_release_files(body: McpReleaseFilesRequest) -> dict[str, Any]:
    try:
        return code_history.release_mcp_files(
            owner=CODE_OPERATOR_ACTOR, files=body.files, note=body.note
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/mcp-locks/release-task")
def mcp_release_task(body: McpReleaseTaskRequest) -> dict[str, Any]:
    try:
        return code_history.release_mcp_task(
            owner=CODE_OPERATOR_ACTOR, task_id=body.task_id, note=body.note
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/mcp-locks/evidence")
def mcp_append_evidence(body: McpEvidenceRequest) -> dict[str, Any]:
    try:
        return code_history.append_mcp_evidence(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            kind=body.kind,
            summary=body.summary,
            data=body.data,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/write/readiness")
def write_readiness() -> dict[str, Any]:
    return code_history.code_write_readiness()


@router.get("/repo/status")
def repo_status() -> dict[str, Any]:
    return code_history.repo_status()


@router.get("/repo/tree")
def repo_tree(root: str = ".", limit: int = 400) -> dict[str, Any]:
    try:
        return code_history.repo_tree(root=root, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/repo/search")
def repo_search(body: SearchRequest) -> dict[str, Any]:
    try:
        return code_history.search_text(body.pattern, root=body.root, max_results=body.max_results)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"reason": str(exc)}) from exc


@router.post("/files/read")
def read_file(body: ReadFileRequest) -> dict[str, Any]:
    try:
        return code_history.read_file_slice(
            body.relative_path, start_line=body.start_line, line_count=body.line_count
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/patch/proposals")
def propose_patch(body: PatchProposalRequest) -> dict[str, Any]:
    try:
        return code_history.propose_file_replacement(
            body.relative_path,
            body.proposed_text,
            agent_id=CODE_OPERATOR_ACTOR,
            base_sha256=body.base_sha256,
            reason=body.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/patch/apply")
def apply_patch(body: PatchApplyRequest) -> dict[str, Any]:
    try:
        return code_history.apply_patch_proposal(
            body.proposal_id,
            agent_id=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            reason=body.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/patch/apply-reviewed")
def apply_reviewed_patch(body: ReviewedPatchApplyRequest) -> dict[str, Any]:
    try:
        return code_history.apply_reviewed_patch_proposal(
            body.proposal_id,
            agent_id=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            review_proof_ids=body.review_proof_ids,
            reason=body.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/gates")
def list_gates() -> dict[str, Any]:
    try:
        return code_history.list_mcp_gates()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/gates/run")
def run_gate(body: GateRunRequest) -> dict[str, Any]:
    try:
        return code_history.run_mcp_gate(body.gate_id, owner=CODE_OPERATOR_ACTOR, cwd=body.cwd)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/git/readiness")
def git_readiness() -> dict[str, Any]:
    return code_history.git_ship_readiness()


@router.post("/git/branch")
def git_branch(body: GitBranchRequest) -> dict[str, Any]:
    try:
        return code_history.git_create_branch(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            branch_name=body.branch_name,
            base_ref=body.base_ref,
            reason=body.reason,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/git/stage-owned")
def git_stage_owned(body: GitStageRequest) -> dict[str, Any]:
    try:
        return code_history.git_stage_owned_files(
            owner=CODE_OPERATOR_ACTOR, task_id=body.task_id, files=body.files
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/git/commit-owned")
def git_commit_owned(body: GitCommitRequest) -> dict[str, Any]:
    try:
        return code_history.git_commit_owned_files(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            files=body.files,
            message=body.message,
            proof_ids=body.proof_ids,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/git/push")
def git_push(body: GitPushRequest) -> dict[str, Any]:
    try:
        return code_history.git_push_current_branch(
            owner=CODE_OPERATOR_ACTOR, task_id=body.task_id, remote=body.remote
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/git/pr")
def git_pr(body: GitPullRequestRequest) -> dict[str, Any]:
    try:
        return code_history.git_open_pull_request(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            base_ref=body.base_ref,
            title=body.title,
            body=body.body,
            draft=body.draft,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/history/files")
def touched_files(limit: int = 200) -> dict[str, Any]:
    return code_history.list_touched_files(limit=limit)


@router.post("/history/snapshots")
def create_snapshot(body: SnapshotRequest) -> dict[str, Any]:
    try:
        return code_history.snapshot_file(
            body.relative_path,
            agent_id=CODE_OPERATOR_ACTOR,
            action_id=body.action_id,
            reason=body.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/history/list")
def snapshots_for_file(body: SnapshotQuery) -> dict[str, Any]:
    try:
        return code_history.list_snapshots(body.relative_path, limit=body.limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/history/diff/{snapshot_id}")
def snapshot_diff(snapshot_id: str, relative_path: str) -> dict[str, Any]:
    try:
        return code_history.snapshot_diff(relative_path, snapshot_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/history/restore")
def restore_snapshot(body: RestoreRequest) -> dict[str, Any]:
    try:
        return code_history.restore_snapshot(
            body.relative_path,
            body.snapshot_id,
            agent_id=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            reason=body.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


# ---------------------------------------------------------------------------
# Recovery Controller v1 — failure ledger routes (no UI, no autonomous apply,
# no file mutation by the controller). Each route dispatches to code_history
# helpers that append MCP evidence and write the JSONL ledger.
# ---------------------------------------------------------------------------


class RecoveryRecordFailureRequest(StrictBody):
    task_id: str
    failed_step: str = Field(min_length=1, max_length=120)
    failure_class: str
    failure_summary: str = Field(min_length=1, max_length=400)
    failed_step_type: str = "unknown"
    agent_stack: list[str] = Field(default_factory=list)
    resume_from_step: str = ""
    recommended_next_action: str = "none"
    redaction_status: str = "pass"
    worker_output_status: str = "complete"
    context_pack: list[str] = Field(default_factory=list)
    provenance_ids: list[str] = Field(default_factory=list)
    evidence_id: str = ""
    affected_files: list[str] = Field(default_factory=list)
    attempt_n: int = Field(default=1, ge=1)
    max_attempts: int = Field(default=3, ge=1, le=32)


class RecoveryMarkOutcomeRequest(StrictBody):
    attempt_id: str = Field(min_length=32, max_length=32)
    status: str
    recovery_summary: str = Field(min_length=1, max_length=400)
    proposal_id: str | None = None
    review_evidence_id: str | None = None
    apply_evidence_id: str | None = None
    retry_gate_id: str | None = None


@router.post("/recovery/record-failure")
def recovery_record_failure(body: RecoveryRecordFailureRequest) -> dict[str, Any]:
    try:
        return code_history.record_step_failure(
            owner=CODE_OPERATOR_ACTOR,
            task_id=body.task_id,
            failed_step=body.failed_step,
            failure_class=body.failure_class,
            failure_summary=body.failure_summary,
            failed_step_type=body.failed_step_type,
            agent_stack=body.agent_stack,
            resume_from_step=body.resume_from_step,
            recommended_next_action=body.recommended_next_action,
            redaction_status=body.redaction_status,
            worker_output_status=body.worker_output_status,
            context_pack=body.context_pack,
            provenance_ids=body.provenance_ids,
            evidence_id=body.evidence_id,
            affected_files=body.affected_files,
            attempt_n=body.attempt_n,
            max_attempts=body.max_attempts,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/recovery/mark-outcome")
def recovery_mark_outcome(body: RecoveryMarkOutcomeRequest) -> dict[str, Any]:
    try:
        return code_history.mark_recovery_outcome(
            owner=CODE_OPERATOR_ACTOR,
            attempt_id=body.attempt_id,
            status=body.status,
            recovery_summary=body.recovery_summary,
            proposal_id=body.proposal_id,
            review_evidence_id=body.review_evidence_id,
            apply_evidence_id=body.apply_evidence_id,
            retry_gate_id=body.retry_gate_id,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/recovery/state")
def recovery_state(task_id: str | None = None) -> dict[str, Any]:
    try:
        return code_history.list_recovery_attempts(task_id=task_id)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/recovery/runs")
def recovery_runs_active(task_id: str | None = None) -> dict[str, Any]:
    """Return live RC v2 active runs from the in-memory registry.

    BLK-026 fix (Master Continuation Wave Agent D20): Recovery Controller
    v2 commits 1+2 landed in PR #149 but no HTTP route exposed the v2
    enrichment payload (``state``, ``branch``, ``locked_files``,
    ``pre_snapshot_ids``, ``freeze_event_utc``, ``next_action``). The v1
    ``/recovery/state`` only returns the JSONL ledger shape.

    This endpoint is **read-only** — it lists active runs from the
    transient ``_RUNS`` registry. Confirm-by-default policy preserved.
    Mutation routes (propose / review / apply / resume) live below.

    See ``recovery_controller.list_active_runs`` for the payload shape.
    """
    try:
        return recovery_controller.list_active_runs(task_id=task_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


# ---------------------------------------------------------------------------
# W6-2: Recovery Controller v2 active-loop routes (commits 3-5).
#
# Sequence: failure (existing /recovery/record-failure) -> freeze (existing
# saga step in services) -> propose -> review -> apply -> resume.
#
# Each route is a thin wrapper over the corresponding service method
# (``recovery_controller.propose_fix`` / ``review_proposal`` /
# ``apply_proposal`` / ``resume_run``). Validation, redaction, proof
# event emission, and saga compensation all live in the service layer;
# the route's only jobs are body validation, HTTP status mapping, and
# 503-ifying ``ProviderNotConfigured``.
#
# Sources:
#   1. Saga pattern (Garcia-Molina + Salem 1987) -- compensation rule for
#      apply_proposal failure: rollback to RETRY_FAILED, release locks via
#      thaw_run; proposal stays addressable for forensic review.
#      https://temporal.io/blog/saga-pattern-made-easy
#   2. FastAPI router pattern (bigger-applications) -- this file is one
#      APIRouter; the per-feature add is a route block, not a new module.
#      https://fastapi.tiangolo.com/tutorial/bigger-applications/
# ---------------------------------------------------------------------------


# 503 message: intentionally generic so a leaked response body does not
# tell an attacker which env var the operator is missing. The real setup
# guidance lives in HERMES_RC_V2_ACTIVE_LOOP_2026-05-09.md.
_PROVIDER_503_MESSAGE = (
    "Recovery provider is not configured on this server. "
    "An operator must wire a proposal/review provider before this route "
    "can be used. See docs/handoffs/HERMES_RC_V2_ACTIVE_LOOP_2026-05-09.md."
)


class RecoveryProposeRequest(StrictBody):
    """POST /api/code-operator/recovery/propose body."""

    run_id: str = Field(min_length=32, max_length=32)
    failure_summary: str = Field(default="", max_length=400)


class RecoveryReviewRequest(StrictBody):
    """POST /api/code-operator/recovery/review body."""

    run_id: str = Field(min_length=32, max_length=32)
    proposal_id: str = Field(min_length=1, max_length=120)


class RecoveryApplyRequest(StrictBody):
    """POST /api/code-operator/recovery/apply body."""

    run_id: str = Field(min_length=32, max_length=32)
    proposal_id: str = Field(min_length=1, max_length=120)
    confirm: bool = False


class RecoveryResumeRequest(StrictBody):
    """POST /api/code-operator/recovery/resume body."""

    run_id: str = Field(min_length=32, max_length=32)
    gate_id: str | None = Field(default=None, max_length=80)


@router.post("/recovery/propose")
def recovery_propose(body: RecoveryProposeRequest) -> dict[str, Any]:
    """Phase 4 of the active loop: dispatch a fix proposal to the configured provider.

    Returns 200 + ProposalRecord on success, 503 if no provider is wired,
    409 if the run is not in PROPOSING (or not addressable), 422 on shape
    issues. Confirm-by-default policy: this route does NOT auto-apply; a
    follow-up call to /apply with confirm=true is required.
    """
    try:
        result = recovery_controller.propose_fix(
            attempt_id=body.run_id,
            owner=CODE_OPERATOR_ACTOR,
            failure_summary=body.failure_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc

    status = result.get("status")
    if status == "provider_not_configured":
        raise HTTPException(status_code=503, detail={"reason": _PROVIDER_503_MESSAGE})
    if status == "unknown_attempt":
        raise HTTPException(status_code=404, detail={"reason": "Recovery run not found."})
    if status == "not_in_proposing":
        raise HTTPException(
            status_code=409,
            detail={
                "reason": (
                    "Run is not in 'proposing' state; freeze the run first "
                    "via the saga step before requesting a proposal."
                ),
                "current_state": result.get("current_state"),
            },
        )
    return result


@router.post("/recovery/review")
def recovery_review(body: RecoveryReviewRequest) -> dict[str, Any]:
    """Phase 5: adversarial review of the proposal.

    Returns 200 + ReviewRecord(verdict in {"approved","rejected","needs-revision"}).
    A verdict of "approved" transitions the run to AWAITING_HUMAN_CONFIRM.
    """
    try:
        result = recovery_controller.review_proposal(
            attempt_id=body.run_id,
            owner=CODE_OPERATOR_ACTOR,
            proposal_id=body.proposal_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc

    status = result.get("status")
    if status == "provider_not_configured":
        raise HTTPException(status_code=503, detail={"reason": _PROVIDER_503_MESSAGE})
    if status == "unknown_attempt":
        raise HTTPException(status_code=404, detail={"reason": "Recovery run not found."})
    if status == "not_in_reviewing":
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Run is not in 'reviewing' state; propose a fix first.",
                "current_state": result.get("current_state"),
            },
        )
    if status == "proposal_mismatch":
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "proposal_id does not match the run's current proposal.",
                "expected": result.get("expected"),
                "got": result.get("got"),
            },
        )
    return result


@router.post("/recovery/apply")
def recovery_apply(body: RecoveryApplyRequest) -> dict[str, Any]:
    """Phase 6: apply the reviewed proposal.

    Requires verdict='approved' and confirm=true (confirm-by-default
    policy). Returns 409 if the review is rejected or pending, 422 if
    confirm is missing, 200 + ApplyRecord on success.
    """
    try:
        result = recovery_controller.apply_proposal(
            attempt_id=body.run_id,
            owner=CODE_OPERATOR_ACTOR,
            proposal_id=body.proposal_id,
            confirm=body.confirm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc

    status = result.get("status")
    if status == "unknown_attempt":
        raise HTTPException(status_code=404, detail={"reason": "Recovery run not found."})
    if status == "not_ready_to_apply":
        raise HTTPException(
            status_code=409,
            detail={
                "reason": (
                    "Run is not in 'awaiting_human_confirm' state; review the proposal first."
                ),
                "current_state": result.get("current_state"),
            },
        )
    if status == "proposal_mismatch":
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "proposal_id does not match the run's current proposal.",
                "expected": result.get("expected"),
                "got": result.get("got"),
            },
        )
    if status == "review_not_approved":
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Review verdict is not 'approved'; cannot apply.",
                "verdict": result.get("verdict"),
            },
        )
    if status == "confirm_required":
        raise HTTPException(
            status_code=422,
            detail={
                "reason": (
                    "Confirm-by-default: explicit confirm=true is required to "
                    "apply a reviewed patch."
                ),
            },
        )
    if status == "apply_failed":
        # Saga compensation already ran (see service); surface as 502 so
        # the caller can distinguish "we tried and the apply failed" from
        # "we never started the apply".
        raise HTTPException(
            status_code=502,
            detail={
                "reason": "Patch apply failed; run transitioned to retry_failed.",
                "error_class": result.get("error_class"),
                "run": result.get("run"),
            },
        )
    return result


@router.post("/recovery/resume")
def recovery_resume(body: RecoveryResumeRequest) -> dict[str, Any]:
    """Phase 7: re-run the original failing gate.

    Gate passes -> RECOVERED + thaw_run; gate fails -> ESCALATED + thaw_run.
    Both terminal states release the file locks acquired in freeze_run.
    """
    try:
        result = recovery_controller.resume_run(
            attempt_id=body.run_id,
            owner=CODE_OPERATOR_ACTOR,
            gate_id=body.gate_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc

    status = result.get("status")
    if status == "unknown_attempt":
        raise HTTPException(status_code=404, detail={"reason": "Recovery run not found."})
    if status == "not_in_re_running_gate":
        raise HTTPException(
            status_code=409,
            detail={
                "reason": (
                    "Run is not in 're_running_gate' state; apply a reviewed proposal first."
                ),
                "current_state": result.get("current_state"),
            },
        )
    if status == "gate_error":
        raise HTTPException(
            status_code=502,
            detail={
                "reason": "Gate runner raised an exception during resume.",
                "gate_id": result.get("gate_id"),
                "error_class": result.get("error_class"),
            },
        )
    return result


# W18-A21 (2026-05-11): expose team task evidence to the #agents GUI.
# The Hermes Agent code-operator currently writes proof_events rows of kind
# 'code_provider.coding_plan' / 'code_provider.code_review' whenever the
# MiniMax-builders or DeepSeek-reviewers teams produce work. The previous
# UI surfaced only the smoke status and the readiness contract — it never
# rendered the actual team tasks that ran. This read-only endpoint exposes
# the most recent team-task rows so the #agents GUI can render them without
# refresh. It is intentionally minimal: no writes, no auth state change,
# only a paginated read over proof_events.
@router.get("/teams/team-tasks")
def team_tasks(limit: int = 25) -> dict[str, Any]:
    limit = max(1, min(int(limit or 25), 100))
    raw = rows(
        """
        SELECT id, event_type, source_agent, payload, created_at
        FROM proof_events
        WHERE event_type IN (
            'code_provider.coding_plan',
            'code_provider.code_review'
        )
        ORDER BY datetime(created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    items: list[dict[str, Any]] = []
    for record in raw:
        try:
            payload = json.loads(record.get("payload") or "{}")
        except (ValueError, TypeError):
            payload = {}
        event_type = str(record.get("event_type") or "")
        run_type = event_type.split(".", 1)[1] if "." in event_type else event_type
        team_id = str(payload.get("team_id") or "")
        provider_id = str(payload.get("provider_id") or "")
        items.append(
            {
                "id": str(record.get("id") or ""),
                "event_type": event_type,
                "run_type": run_type,
                "team_id": team_id,
                "provider_id": provider_id,
                "task_id": str(payload.get("task_id") or ""),
                "run_id": str(payload.get("run_id") or ""),
                "files": payload.get("files") or [],
                "response_sha256": payload.get("response_sha256"),
                "prompt_sha256": payload.get("prompt_sha256"),
                "ts_utc": str(record.get("created_at") or ""),
                "source_agent": str(record.get("source_agent") or ""),
            }
        )
    return {
        "count": len(items),
        "items": items,
        "supported_event_types": [
            "code_provider.coding_plan",
            "code_provider.code_review",
        ],
    }


@router.get("/teams/provider-smoke-history")
def team_provider_smoke_history(limit: int = 25) -> dict[str, Any]:
    """Return the most recent code_provider_smoke evidence summaries.

    Reads the local provider-smoke-status.json file (one record per
    provider; latest only). For a complete history we also include the
    most recent provider-runs JSON artifacts as files-by-path so the GUI
    can show which teams have actually executed coding/review passes.
    """
    limit = max(1, min(int(limit or 25), 100))
    status_path = (
        code_history.IMPLEMENTATION_ROOT / "var" / "code-history" / "provider-smoke-status.json"
    )
    smoke: list[dict[str, Any]] = []
    try:
        raw = json.loads(status_path.read_text(encoding="utf-8"))
        providers = raw.get("providers") if isinstance(raw, dict) else None
        if isinstance(providers, dict):
            for provider_id, record in providers.items():
                if not isinstance(record, dict):
                    continue
                auth = (
                    record.get("auth_contract")
                    if isinstance(record.get("auth_contract"), dict)
                    else {}
                )
                smoke.append(
                    {
                        "provider_id": str(provider_id),
                        "status": str(record.get("status") or ""),
                        "accepted": bool(record.get("accepted")),
                        "ts_utc": str(record.get("ts_utc") or ""),
                        "evidence_id": record.get("evidence_id"),
                        "content_sha256": record.get("content_sha256"),
                        "base_url_label": auth.get("base_url_label"),
                        "model": auth.get("model"),
                        "blocked_reasons": list(record.get("blocked_reasons") or [])[:3],
                    }
                )
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        smoke = []
    smoke.sort(key=lambda item: item.get("ts_utc") or "", reverse=True)
    return {
        "count": len(smoke[:limit]),
        "items": smoke[:limit],
        "source": "var/code-history/provider-smoke-status.json",
    }
