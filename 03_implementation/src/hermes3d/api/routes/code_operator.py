"""Hermes Agent code-operation APIs for source-backed programming work."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from hermes3d.services import code_history

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


class AgentE2EJobRequest(StrictBody):
    task_id: str
    title: str = Field(min_length=1, max_length=180)
    files: list[str] = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=2400)
    target_branch: str | None = None
    role_chain: list[str] = Field(default_factory=lambda: ["finder", "builder", "reviewer", "tester"])
    cli_worker: str | None = None
    release_on_finish: bool = True


@router.get("/programming-readiness")
def programming_readiness() -> dict[str, Any]:
    return code_history.programming_readiness()


@router.get("/e2e/readiness")
def agent_e2e_readiness() -> dict[str, Any]:
    return code_history.agent_e2e_readiness()


@router.get("/cli-runners")
def code_cli_runners() -> dict[str, Any]:
    return code_history.code_cli_runners()


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
        return code_history.release_mcp_files(owner=CODE_OPERATOR_ACTOR, files=body.files, note=body.note)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/mcp-locks/release-task")
def mcp_release_task(body: McpReleaseTaskRequest) -> dict[str, Any]:
    try:
        return code_history.release_mcp_task(owner=CODE_OPERATOR_ACTOR, task_id=body.task_id, note=body.note)
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
        return code_history.read_file_slice(body.relative_path, start_line=body.start_line, line_count=body.line_count)
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
        return code_history.git_stage_owned_files(owner=CODE_OPERATOR_ACTOR, task_id=body.task_id, files=body.files)
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
        return code_history.git_push_current_branch(owner=CODE_OPERATOR_ACTOR, task_id=body.task_id, remote=body.remote)
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
