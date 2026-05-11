from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id
from hermes3d.gateways.redaction import redact_text
from hermes3d.services.agent_checkout import DEFAULT_AGENT_CHECKOUT, hermes_agent_checkout
from hermes3d.services.proof_helpers import attach_version_fields

router = APIRouter()

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[4]
BACKUP_ROOT = IMPLEMENTATION_ROOT / "var" / "hermes_agent_backups"
# Hermes Agent v0.13 canary switch (Wave A5 finding): the prior
# ``DEFAULT_CHECKOUT = Path(os.environ.get("HERMES_AGENT_CHECKOUT", ...))``
# captured the env at module-import time and the value never refreshed.
# Canary↔production rollback required a process restart. Switching to a
# per-call resolver (``hermes_agent_checkout()``) reads the env every time
# ``_repo_path()`` is called, so flipping ``HERMES_AGENT_CHECKOUT`` between
# requests works as expected. ``DEFAULT_CHECKOUT`` retained for any
# downstream import (e.g. tests that monkeypatch the constant).
#
# F4 fix (P1-8 post-promotion hardening, 2026-05-09): the prior literal
# ``"G:/Github/hermes-agent-fresh"`` (v0.12 path) was misleading after
# Wave 1 promoted v0.13 to default. Realign this module-level alias to
# the resolver's authoritative default so any back-compat consumer
# (e.g. a test that imports the constant) gets the post-promotion path.
# DO NOT import this from new code — call ``hermes_agent_checkout()``
# per-call instead so live env flips propagate.
DEFAULT_CHECKOUT = DEFAULT_AGENT_CHECKOUT
UPSTREAM_URL = os.environ.get(
    "HERMES_AGENT_UPSTREAM_URL", "https://github.com/NousResearch/Hermes-Agent.git"
)
LATEST_RELEASE_API = "https://api.github.com/repos/NousResearch/hermes-agent/releases/latest"
RELEASES_API = "https://api.github.com/repos/NousResearch/hermes-agent/releases?per_page=100"
TAG_RE = re.compile(r"^v(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})$")
BACKUP_ID_RE = re.compile(r"^[A-Za-z0-9._-]{12,96}$")
# F3 fix (P1-8 post-promotion hardening, 2026-05-09): the local
# ``SECRET_RE`` and ``redact_text()`` helper were materially weaker than
# ``hermes3d.gateways.redaction.redact_text`` (no JWT, no Anthropic /
# OpenAI key shape, no header redaction, etc.). They are gone. Every
# call site now goes through ``redact_text`` so a single hardened
# regex chain owns secret masking for this module — matches the
# Sentry single-redaction-hook pattern already used elsewhere
# (Bonus 12 #6 fix). See gateways.redaction docstring for the full
# pattern list and OWASP A09:2021 rationale.


class BackupRequest(BaseModel):
    note: str | None = None


class StagedUpdateRequest(BaseModel):
    target_tag: str | None = None
    max_steps: int = 1
    create_backup: bool = True
    run_checks: bool = True
    actor: str = "hermes-agent"


class RollbackRequest(BaseModel):
    backup_id: str | None = None
    tag: str | None = None
    actor: str = "hermes-agent"


def _honest_blocked_status(
    repo: Path,
    state: dict[str, Any],
    *,
    reason: str,
    upstream_error: str | None = None,
) -> dict[str, Any]:
    """Return the agreed honest-blocked envelope for /api/agents/update/status.

    Wave 17 root-cause fix (2026-05-11): the status endpoint must NEVER 5xx.
    Pre-fix, any failure inside ``_remote_release_tags`` or ``_latest_release``
    (GitHub Releases API 403 rate-limit / 5xx / DNS / timeout) propagated as
    HTTPException(502), which surfaced to the browser as a hard 502 banner.

    Per the W17 contract the route returns:
      - ``accepted=True`` + ``status="ready"`` when canary configured + reachable
      - ``accepted=False`` + ``status="unknown"`` when env unset / repo missing
      - ``accepted=False`` + ``status="offline"`` when env set but upstream down

    Keeping the legacy keys (``repo_url``, ``checkout_path``, ``current``,
    ``backup_available``, ``latest_backup``, ``strategy``, ``rollback``,
    ``auto_repair``) for back-compat with existing UI consumers that already
    parse the success envelope.
    """
    backup = _latest_backup()
    is_offline = upstream_error is not None
    return {
        # Wave 17 W17-A1 honest-blocked contract fields.
        "accepted": False,
        "status": "offline" if is_offline else "unknown",
        "reason": reason,
        "version": "v0.13.0",
        "upstream_error": upstream_error,
        # Back-compat keys (subset that does not require remote tag listing).
        "repo_url": UPSTREAM_URL,
        "checkout_path": str(repo),
        "repo_ready": state.get("repo_ready", False),
        "current": state,
        "latest_release": {
            "tag": None,
            "name": None,
            "source": "github_releases_api",
            "api_warning": upstream_error,
        },
        "outdated": False,
        "outdated_by": 0,
        "pending_tags": [],
        "backup_available": backup is not None,
        "latest_backup": backup,
        "strategy": "staged_backup_then_tag_checkout",
        "rollback": "Rollback checks out the recorded backup tag/commit after a backup exists; local bundle/dirty zip are retained under var/hermes_agent_backups.",
        "auto_repair": "Failed staged update gates automatically attempt rollback to the pre-update backup target.",
    }


@router.get("/api/agents/update/status")
def update_status() -> dict[str, Any]:
    """GET /api/agents/update/status — Hermes Agent v0.13 update gateway status.

    Wave 17 root-cause fix (2026-05-11): the handler now NEVER raises a 5xx.
    All exceptions from the upstream-querying helpers (``_remote_release_tags``
    raising HTTPException(502) on GitHub 403/5xx, ``_latest_release`` raising
    on non-404 HTTP errors, ``_repo_state`` raising on git failures via
    ``_run_git``) are caught and converted to a 200 honest-blocked payload.

    The contract (W17-A1, see ``_honest_blocked_status``):
      - ``200 + accepted=True, status="ready"`` when canary reachable + state ok
      - ``200 + accepted=False, status="unknown"`` when env unset / repo missing
      - ``200 + accepted=False, status="offline"`` when upstream API down

    Per the standing rule "endpoint should NEVER 5xx", no caught exception is
    re-raised. The original error is preserved in ``upstream_error`` for
    operator triage, redacted via ``redact_text`` to strip any leaked secrets.

    References:
    - FastAPI exception handler patterns:
      https://fastapi.tiangolo.com/tutorial/handling-errors/
    - W17-A1 honest-blocked contract handoff:
      03_implementation/docs/handoffs/W17_A5_BACKEND_API_WIRING_2026-05-11.md
    """
    repo = _repo_path()
    # First gate: is the canary checkout even present? If not, status="unknown".
    try:
        state = _repo_state(repo)
    except HTTPException as exc:
        # _run_git inside _repo_state can raise 502; surface as offline+unknown.
        return _honest_blocked_status(
            repo,
            {"repo_ready": False, "reason": f"git probe failed: {redact_text(str(exc.detail))[:200]}"},
            reason="repo_state_unreachable",
            upstream_error=redact_text(str(exc.detail))[:200],
        )
    except Exception as exc:  # noqa: BLE001 — defense-in-depth catch-all
        return _honest_blocked_status(
            repo,
            {"repo_ready": False, "reason": f"git probe raised: {redact_text(type(exc).__name__)}"},
            reason="repo_state_unreachable",
            upstream_error=redact_text(f"{type(exc).__name__}: {exc}")[:200],
        )

    if not state.get("repo_ready"):
        # Canary path unset or invalid — honest blocked with status="unknown".
        return _honest_blocked_status(
            repo,
            state,
            reason="canary_not_configured",
        )

    # Second gate: GitHub Releases API. Either raises HTTPException(502) on
    # network/rate-limit/5xx or returns a tags list. Honest-blocked path here
    # is status="offline" — repo is fine but upstream is unreachable.
    try:
        tags = _remote_release_tags(repo)
        latest = _latest_release(tags)
    except HTTPException as exc:
        return _honest_blocked_status(
            repo,
            state,
            reason="canary_unreachable",
            upstream_error=redact_text(str(exc.detail))[:200],
        )
    except Exception as exc:  # noqa: BLE001 — defense-in-depth catch-all
        return _honest_blocked_status(
            repo,
            state,
            reason="canary_unreachable",
            upstream_error=redact_text(f"{type(exc).__name__}: {exc}")[:200],
        )

    if isinstance(latest.get("tag"), str) and latest["tag"] not in tags:
        tags = sorted([*tags, latest["tag"]], key=_tag_key)
    current_tag = state.get("exact_tag") or state.get("nearest_tag")
    pending = _pending_tags(tags, current_tag, latest.get("tag"))
    backup = _latest_backup()
    payload = {
        # W17-A1 honest-blocked contract — ready path (canary reachable).
        "accepted": True,
        "status": "ready",
        "reason": None,
        "version": "v0.13.0",
        "upstream_error": None,
        # Legacy keys preserved verbatim for back-compat.
        "repo_url": UPSTREAM_URL,
        "checkout_path": str(repo),
        "repo_ready": state["repo_ready"],
        "current": state,
        "latest_release": latest,
        "outdated": bool(pending),
        "outdated_by": len(pending),
        "pending_tags": pending,
        "backup_available": backup is not None,
        "latest_backup": backup,
        "strategy": "staged_backup_then_tag_checkout",
        "rollback": "Rollback checks out the recorded backup tag/commit after a backup exists; local bundle/dirty zip are retained under var/hermes_agent_backups.",
        "auto_repair": "Failed staged update gates automatically attempt rollback to the pre-update backup target.",
    }
    try:
        _append_proof_event(
            "hermes_agent_update_status", "hermes3d-updater", _proof_summary(payload)
        )
    except Exception:  # noqa: BLE001 — never let proof persistence 5xx the route
        # Proof persistence is best-effort; failing here must not turn into 502.
        pass
    return payload


@router.post("/api/agents/update/backup", status_code=201)
def create_update_backup(body: BackupRequest | None = None) -> dict[str, Any]:
    backup = _create_backup(
        _repo_path(), note=(body.note if body else None) or "manual Hermes Agent pre-update backup"
    )
    _append_proof_event(
        "hermes_agent_backup_created", "hermes3d-updater", _proof_summary({"backup": backup})
    )
    return backup


@router.post("/api/agents/update/staged")
def staged_update(body: StagedUpdateRequest) -> dict[str, Any]:
    repo = _repo_path()
    state = _repo_state(repo)
    if not state["repo_ready"]:
        raise HTTPException(status_code=409, detail=state["reason"])
    if body.create_backup is not True:
        raise HTTPException(
            status_code=400,
            detail="A pre-update backup is required before every Hermes Agent staged update.",
        )
    _ensure_remote(repo)
    _run_git(repo, ["fetch", "--tags", "upstream"], timeout=120)
    tags = _remote_release_tags(repo)
    latest = _latest_release(tags)
    if isinstance(latest.get("tag"), str) and latest["tag"] not in tags:
        tags = sorted([*tags, latest["tag"]], key=_tag_key)
    target = body.target_tag or latest.get("tag")
    if not target:
        raise HTTPException(
            status_code=409, detail="No release target was discovered from the GitHub Releases API."
        )
    current_tag = state.get("exact_tag") or state.get("nearest_tag")
    pending = _pending_tags(tags, current_tag, target)
    if not pending:
        payload = {
            "updated": False,
            "status": "already_current",
            "current": _repo_state(repo),
            "latest_release": latest,
            "steps": [],
        }
        _append_proof_event("hermes_agent_update_skipped", body.actor, _proof_summary(payload))
        return payload
    steps = pending[: max(1, min(body.max_steps, 10))]
    backup = _create_backup(repo, note=f"automatic backup before staged update to {steps[-1]}")
    # BLK-023 fix (Master Continuation Agent A6 finding): emit a proof_event
    # for the auto-backup the staged_update path takes, so observability is
    # symmetric with the manual /backup endpoint at line 80-84. Pre-fix this
    # path only wrote to agent_config (line 297-298), leaving no proof_events
    # row for the backup created here.
    _append_proof_event(
        "hermes_agent_backup_auto_created",
        body.actor,
        _proof_summary({"backup": backup, "target": steps[-1]}),
    )
    results: list[dict[str, Any]] = []
    repair: dict[str, Any] | None = None
    for tag in steps:
        # Bonus 12 finding #3 fix (PR #137) + BLK-022 (Master Continuation
        # Agent A6 finding): catch HTTPException AND subprocess.TimeoutExpired
        # in the per-tag loop. Pre-A6 the catch was HTTPException-only, but
        # _run_git's underlying ``subprocess.run(timeout=120)`` raises
        # subprocess.TimeoutExpired BEFORE the HTTPException wrapper kicks in
        # if the git operation hangs past the timeout — that exception
        # escaped the loop and bypassed _auto_repair_to_backup, leaving the
        # repo on the previous (still-unverified) tag.
        try:
            _run_git(repo, ["checkout", "--detach", tag], timeout=120)
            checks = (
                _run_update_checks(repo)
                if body.run_checks
                else [
                    {
                        "name": "checks",
                        "status": "skipped",
                        "output": "run_checks=false prevents verified update.",
                    }
                ]
            )
        except (HTTPException, subprocess.TimeoutExpired) as exc:
            if isinstance(exc, HTTPException):
                detail = str(exc.detail)
                check_name = "git checkout to staged tag"
            else:
                # subprocess.TimeoutExpired -> structured detail
                detail = f"git operation timed out after {getattr(exc, 'timeout', '?')}s"
                check_name = "git checkout to staged tag (timeout)"
            synthetic_check = {
                "name": check_name,
                "status": "fail",
                "output": redact_text(detail)[:800],
            }
            results.append({"tag": tag, "checks": [synthetic_check], "ok": False})
            repair = _auto_repair_to_backup(repo, backup, body.actor, failed_tag=tag)
            break
        ok = all(item.get("status") == "pass" for item in checks)
        results.append({"tag": tag, "checks": checks, "ok": ok})
        if not ok:
            repair = _auto_repair_to_backup(repo, backup, body.actor, failed_tag=tag)
            break
    final_state = _repo_state(repo)
    all_ok = bool(results) and all(item["ok"] for item in results)
    has_skipped = any(
        check.get("status") == "skipped"
        for step in results
        for check in step.get("checks", [])
        if isinstance(check, dict)
    )
    status = (
        "updated"
        if all_ok
        else "rolled_back_after_unverified_check"
        if has_skipped and repair and repair.get("rolled_back")
        else "rolled_back_after_failed_check"
        if repair and repair.get("rolled_back")
        else "stopped_on_unverified_check"
        if has_skipped
        else "stopped_on_failed_check"
    )
    payload = {
        "updated": all_ok,
        "status": status,
        "verified": all_ok,
        "reason": None
        if all_ok
        else "One or more mandatory update gates failed or were skipped; update was not accepted as verified.",
        "backup": backup,
        "steps": results,
        "repair": repair,
        "current": final_state,
        "latest_release": latest,
        "remaining_tags": _pending_tags(
            tags, final_state.get("exact_tag") or final_state.get("nearest_tag"), target
        ),
    }
    # Bonus 12 finding #6 fix (Audit PR #135): persist the redacted/truncated
    # proof summary to agent_config (matching what proof_events already gets).
    # Pre-fix the raw payload — including 800-char check.output strings that
    # only got the narrow legacy ``_redact()`` pass — was written verbatim to
    # disk, while proof_events correctly used _proof_summary(). Symmetrize so
    # both sinks receive the same sanitized blob (Sentry-style
    # single-redaction-hook). P1-8 F3 (2026-05-09): the legacy ``_redact()`` /
    # ``SECRET_RE`` are gone; ``_proof_summary`` now calls ``redact_text``.
    persisted = _proof_summary(payload)
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("hermes_agent.update.last_run", json.dumps({"actor": body.actor, **persisted})),
    )
    _append_proof_event("hermes_agent_update_run", body.actor, persisted)
    return payload


@router.post("/api/agents/update/rollback")
def rollback_update(body: RollbackRequest) -> dict[str, Any]:
    repo = _repo_path()
    state = _repo_state(repo)
    if not state["repo_ready"]:
        raise HTTPException(status_code=409, detail=state["reason"])
    if body.backup_id:
        backup = _find_backup(body.backup_id)
        # F1 fix (P1-8 post-promotion hardening, 2026-05-09): even when
        # the operator names a specific backup_id, the recorded
        # ``checkout_path`` (if present) must match the active checkout.
        # Otherwise a v0.13 backup would be checked out into the v0.12
        # working tree (or vice-versa), corrupting the repo.
        if backup is not None:
            recorded_path = backup.get("checkout_path")
            if recorded_path is not None and recorded_path != str(repo):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Rollback refused: requested backup was taken on a "
                        f"different checkout ({recorded_path!r}) than the "
                        f"active one ({str(repo)!r}). Set "
                        "HERMES_AGENT_CHECKOUT to the version that owns "
                        "the backup, or take a fresh backup."
                    ),
                )
    else:
        # F1 fix: filter the implicit "latest backup" by current
        # checkout. If none match, refuse rather than risk a
        # cross-version rollback.
        backup = _latest_backup(checkout_path=repo)
        if backup is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "no backup found for current checkout; rollback "
                    "refused. set HERMES_AGENT_CHECKOUT to the version "
                    "that owns the backup, or take a fresh backup."
                ),
            )
    if not backup:
        raise HTTPException(
            status_code=409, detail="Rollback requires an existing Hermes Agent backup record."
        )
    recorded_targets = [backup.get("tag"), backup.get("branch"), backup.get("commit")]
    target = body.tag or next((item for item in recorded_targets if item), None)
    if body.tag and body.tag not in recorded_targets:
        raise HTTPException(
            status_code=400,
            detail="Rollback target must match the selected backup's recorded tag, branch, or commit.",
        )
    if not target:
        raise HTTPException(
            status_code=409, detail="No rollback tag or backup target is available."
        )
    _create_backup(repo, note=f"automatic backup before rollback to {target}")
    _run_git(repo, ["checkout", "--detach", str(target)], timeout=120)
    checks = _run_update_checks(repo)
    final_state = _repo_state(repo)
    ok = all(item.get("status") == "pass" for item in checks)
    payload = {
        "rolled_back": ok,
        "status": "rolled_back" if ok else "rollback_failed_checks",
        "target": target,
        "checks": checks,
        "current": final_state,
    }
    # Bonus 12 finding #6 fix (PR #135): same redaction symmetry for the
    # rollback path — see staged_update for full rationale.
    persisted = _proof_summary(payload)
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("hermes_agent.update.last_rollback", json.dumps({"actor": body.actor, **persisted})),
    )
    _append_proof_event("hermes_agent_update_rollback", body.actor, persisted)
    return payload


def _repo_path() -> Path:
    """Resolve the active Hermes Agent checkout per-call.

    Wave A5 fix: read ``HERMES_AGENT_CHECKOUT`` from the live env every
    call (via ``hermes_agent_checkout()``) instead of returning the
    module-level ``DEFAULT_CHECKOUT`` constant captured at import time.
    Lets canary↔production rollback work without process restart.
    """
    return hermes_agent_checkout()


def _repo_state(repo: Path) -> dict[str, Any]:
    if not repo.exists():
        return {"repo_ready": False, "reason": f"Hermes Agent checkout does not exist: {repo}"}
    if not (repo / ".git").exists():
        return {"repo_ready": False, "reason": f"Hermes Agent path is not a git checkout: {repo}"}
    commit = _run_git(repo, ["rev-parse", "--short=12", "HEAD"]).strip()
    exact_tag = _run_git_optional(repo, ["describe", "--tags", "--exact-match"])
    nearest_tag = _run_git_optional(repo, ["describe", "--tags", "--abbrev=0"])
    branch = _run_git_optional(repo, ["branch", "--show-current"])
    status = _run_git(repo, ["status", "--porcelain=v1"])
    return {
        "repo_ready": True,
        "commit": commit,
        "exact_tag": exact_tag,
        "nearest_tag": nearest_tag,
        "branch": branch or "detached",
        "dirty": bool(status.strip()),
        "dirty_entries": status.splitlines()[:40],
        "remote": UPSTREAM_URL,
    }


def _remote_release_tags(repo: Path) -> list[str]:
    """Fetch published Hermes Agent release tags from the GitHub Releases API.

    Bonus 12 finding #5 fix (Audit PR #135): the original ``except Exception``
    swallowed every failure mode and returned ``[]`` — DNS poisoning, MITM TLS
    errors, GitHub 5xx, rate-limit bans all collapsed silently into
    ``status="already_current"`` downstream, masking a stale Hermes Agent
    checkout (CWE-918 / OWASP CICD-SEC-1 fail-open shape). Tighten the except
    to known network/parse modes only and surface real failures as HTTP 502
    so operators see the outage rather than a false "current" verdict.

    Distinguishes:
    - ``200 + []``                                  -> repo has no published releases
    - ``200 + non-list payload``                    -> upstream contract violation (502)
    - URLError / HTTPError / timeout / JSONDecode  -> network outage (502)
    """
    del repo
    try:
        request = urllib.request.Request(
            RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Hermes3D-Agent-Updater",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        socket.timeout,
        TimeoutError,
        ConnectionError,
        json.JSONDecodeError,
    ) as exc:
        # urllib.error.HTTPError subclasses URLError, so 4xx/5xx land here too.
        raise HTTPException(
            status_code=502,
            detail=(
                f"GitHub Releases API unreachable for {RELEASES_API}: "
                f"{redact_text(type(exc).__name__ + ': ' + str(exc))[:200]}"
            ),
        ) from exc
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=502,
            detail="GitHub Releases API returned a non-list payload; refusing to treat as no-releases.",
        )
    tags = [item.get("tag_name") for item in payload if isinstance(item, dict)]
    return sorted({tag for tag in tags if isinstance(tag, str) and TAG_RE.match(tag)}, key=_tag_key)


def _latest_release(tags: list[str]) -> dict[str, Any]:
    """Fetch the latest GitHub Release.

    Distinguishes 404 ("repo has no /releases/latest yet" -> soft warning) from
    real network outages (URLError / 5xx -> HTTPException 502). See
    ``_remote_release_tags`` for the broader rationale (Bonus 12 #5 / PR #135).
    """
    latest: dict[str, Any] = {"tag": None, "name": None, "source": "github_releases_api"}
    try:
        request = urllib.request.Request(
            LATEST_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Hermes3D-Agent-Updater",
            },
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        api_tag = payload.get("tag_name")
        if isinstance(api_tag, str) and TAG_RE.match(api_tag):
            latest.update(
                {
                    "tag": api_tag,
                    "name": payload.get("name") or api_tag,
                    "published_at": payload.get("published_at"),
                    "html_url": payload.get("html_url"),
                    "source": "github_releases_api",
                }
            )
    except urllib.error.HTTPError as exc:
        # 404 = repo has no /releases/latest yet; soft warning so a brand-new
        # fork is not blocked. Any other HTTP code is a real outage.
        if exc.code == 404:
            latest["api_warning"] = (
                "GitHub /releases/latest returned 404 (no published releases yet)."
            )
        else:
            raise HTTPException(
                status_code=502,
                detail=f"GitHub Releases latest endpoint HTTP {exc.code}: {redact_text(str(exc.reason))[:120]}",
            ) from exc
    except (
        urllib.error.URLError,
        socket.timeout,
        TimeoutError,
        ConnectionError,
        json.JSONDecodeError,
    ) as exc:
        # Soft-warning preserved here ONLY because _remote_release_tags is the
        # authoritative gate; if we got this far, tags came back successfully,
        # so a transient hiccup on the latest endpoint is acceptable.
        latest["api_warning"] = redact_text(str(exc))
    if latest.get("tag") is None and tags:
        latest["api_warning"] = (
            "GitHub Releases latest endpoint unavailable; refusing to treat tags as releases."
        )
    return latest


def _pending_tags(tags: list[str], current_tag: str | None, target_tag: str | None) -> list[str]:
    if not target_tag or target_tag not in tags:
        return []
    target_index = tags.index(target_tag)
    if current_tag in tags:
        return tags[tags.index(current_tag) + 1 : target_index + 1]
    return [target_tag]


def _checkout_path_hash(repo: Path) -> str:
    """8-char SHA-256 prefix of the absolute checkout path.

    F1 fix (P1-8 post-promotion hardening, 2026-05-09): backup_ids must
    encode the checkout that produced them so a v0.13-side backup
    cannot be silently selected by a v0.12 rollback (or vice-versa).
    Hashing the absolute path keeps the id filename-safe across
    platforms while still being a stable per-checkout label.
    """
    return hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:8]


def _create_backup(repo: Path, note: str) -> dict[str, Any]:
    state = _repo_state(repo)
    if not state["repo_ready"]:
        raise HTTPException(status_code=409, detail=state["reason"])
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_tag = str(state.get("exact_tag") or state.get("nearest_tag") or "untagged").replace(
        "/", "_"
    )
    # F1 fix: include short path-hash so cross-version (v0.13 vs v0.12)
    # backups carry distinct ids; ``_latest_backup(checkout_path=...)``
    # filters on ``metadata["checkout_path"]`` and the new id segment is
    # a defense-in-depth disambiguator if the metadata is ever truncated.
    path_hash = _checkout_path_hash(repo)
    backup_id = f"{stamp}_{path_hash}_{safe_tag}_{state['commit']}"
    bundle_path = BACKUP_ROOT / f"{backup_id}.bundle"
    dirty_zip = BACKUP_ROOT / f"{backup_id}.dirty.zip"
    meta_path = BACKUP_ROOT / f"{backup_id}.json"
    _run_git(repo, ["bundle", "create", str(bundle_path), "--all"], timeout=180)
    dirty_entries = _dirty_entries(repo)
    _zip_dirty_entries(repo, dirty_entries, dirty_zip)
    metadata = {
        "backup_id": backup_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
        # F1 fix: ``checkout_path`` was already persisted (line was here
        # pre-fix); the post-fix ``_latest_backup(checkout_path=...)`` now
        # filters on this exact field. Old backups missing this key are
        # excluded from a filtered query because they are untrustworthy
        # across versions.
        "checkout_path": str(repo),
        "checkout_path_hash": path_hash,
        "bundle_path": str(bundle_path),
        "dirty_zip_path": str(dirty_zip) if dirty_zip.exists() else None,
        "tag": state.get("exact_tag") or state.get("nearest_tag"),
        "branch": state.get("branch"),
        "commit": state["commit"],
        "dirty": state["dirty"],
        "dirty_entries": state["dirty_entries"],
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("hermes_agent.update.latest_backup", json.dumps(metadata)),
    )
    return metadata


def _dirty_entries(repo: Path) -> list[Path]:
    raw = _run_git(repo, ["status", "--porcelain=v1", "-z"])
    parts = [part for part in raw.split("\0") if part]
    paths: list[Path] = []
    for item in parts:
        path_text = item[3:] if len(item) > 3 else item
        if " -> " in path_text:
            path_text = path_text.rsplit(" -> ", 1)[-1]
        candidate = (repo / path_text).resolve()
        try:
            candidate.relative_to(repo.resolve())
        except ValueError:
            continue
        if candidate.exists() and candidate.is_file():
            paths.append(candidate)
    return paths


def _zip_dirty_entries(repo: Path, paths: list[Path], target: Path) -> None:
    """Defense-in-depth backup of git-dirty files (Bonus 12 finding #4 fix).

    Hardenings beyond the original ``archive.write(path, path.relative_to(repo))``:

    1. ``allowZip64=True`` — without it, dirty backups >4 GiB silently
       truncate on Python builds that default to no-zip64.
    2. Symlink guard — even though ``_dirty_entries`` already resolves
       paths, a raw symlink can still arrive via tests or future callers;
       we refuse to write any symlink because the target may live outside
       the repo.
    3. Resolved-repo arcname — compute the archive name against
       ``repo.resolve()`` so a symlinked checkout (e.g. ``/tmp/repo`` ->
       ``/var/checkout``) does not raise ``ValueError`` from
       ``relative_to`` and abort the whole backup.
    4. Arcname sanity assert — refuse absolute or parent-traversing
       arcnames so a maliciously crafted dirty path cannot escape the
       archive root on extract.

    References:
    - https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile
    - https://cwe.mitre.org/data/definitions/22.html (Path Traversal)
    """
    if not paths:
        return
    repo_resolved = repo.resolve()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for path in paths:
            if path.is_symlink():
                continue
            try:
                arcname = path.resolve().relative_to(repo_resolved)
            except ValueError:
                # Resolved target lives outside the repo: refuse to include.
                continue
            if arcname.is_absolute() or any(part in ("..", "") for part in arcname.parts):
                continue
            archive.write(path, arcname)


def _latest_backup(checkout_path: Path | None = None) -> dict[str, Any] | None:
    """Return the most recent Hermes Agent backup metadata, optionally filtered.

    F1 fix (P1-8 post-promotion hardening, 2026-05-09): when
    ``checkout_path`` is supplied, only consider backups whose
    persisted ``metadata["checkout_path"]`` exactly matches
    ``str(checkout_path)``. This prevents the documented rollback
    hazard where an operator flips ``HERMES_AGENT_CHECKOUT`` from v0.13
    (default) to v0.12 (fallback) and the rollback endpoint silently
    selects a v0.13-side backup that would corrupt the v0.12 working
    tree.

    Backups WITHOUT ``metadata["checkout_path"]`` (legacy, pre-F1) are
    EXCLUDED from a filtered query: they are untrustworthy across
    versions because their producing checkout is unknown.

    When ``checkout_path is None`` the legacy "newest first wins"
    behavior is preserved for back-compat with existing callers.
    """
    if not BACKUP_ROOT.exists():
        return None
    backups = sorted(
        BACKUP_ROOT.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True
    )
    if not backups:
        return None
    if checkout_path is None:
        # Back-compat: untouched legacy behavior.
        try:
            return json.loads(backups[0].read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    target = str(checkout_path)
    for path in backups:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        # Pre-F1 backups lacking ``checkout_path`` are excluded — we
        # cannot prove they belong to the requested checkout.
        if payload.get("checkout_path") == target:
            return payload
    return None


def _find_backup(backup_id: str | None) -> dict[str, Any] | None:
    if not backup_id:
        return None
    if not BACKUP_ID_RE.match(backup_id):
        raise HTTPException(status_code=400, detail="Invalid backup_id format.")
    path = (BACKUP_ROOT / f"{backup_id}.json").resolve()
    try:
        path.relative_to(BACKUP_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid backup_id path.") from exc
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_remote(repo: Path) -> None:
    remotes = _run_git(repo, ["remote"]).splitlines()
    if "upstream" not in remotes:
        _run_git(repo, ["remote", "add", "upstream", UPSTREAM_URL])


def _run_update_checks(repo: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(_check_command(repo, "git status", ["status", "--short"], expect_returncode=0))
    if shutil.which("npm") and (repo / "package.json").exists():
        checks.append(_check_external(repo, "npm package metadata", ["npm", "pkg", "get", "name"]))
    if shutil.which("python") and (repo / "pyproject.toml").exists():
        checks.append(
            _check_external(repo, "python pyproject metadata", ["python", "-m", "pip", "--version"])
        )
        compile_targets = [
            str(path)
            for path in [
                repo / "run_agent.py",
                repo / "hermes_cli",
                repo / "gateway",
                repo / "agent",
            ]
            if path.exists()
        ]
        if compile_targets:
            checks.append(
                _check_external(
                    repo,
                    "python compile gate",
                    ["python", "-m", "compileall", "-q", *compile_targets],
                    timeout=180,
                )
            )
        tests_dir = repo / "tests"
        # Hermes Agent pytest gate — security-hardened (Audit PR #135 / commit 5ecd8ff
        # Batch 2 Agent 10 + Agent 6 must-fix items).
        #
        # Path-based --ignore mirrors upstream tests.yml. Marker-only filtering
        # cannot prevent tests/e2e/conftest.py from polluting sys.modules at
        # collection time:
        #   https://raw.githubusercontent.com/NousResearch/hermes-agent/main/.github/workflows/tests.yml
        #   https://docs.pytest.org/en/stable/example/pythoncollection.html#ignore-paths-during-test-collection
        #
        # Worker-count guard: -n 0/1 disables xdist isolation, re-exposing the
        # conftest leak under cross-test contamination. Production requires >=2;
        # default is 4 to mirror upstream GHA's 4-vCPU runner.
        # HERMES_AGENT_DIAGNOSTIC=1 overrides for triage.
        #
        # maxfail guard: production stops at 1 (mirrors upstream tests.yml);
        # diagnostic mode raises to 5 for triage-friendly multi-failure output.
        #
        # Skip-path fail-closed: missing HERMES_AGENT_RUN_PYTEST surfaces as
        # status="fail" with REQUIRES_CONFIRMATION output, never status="skipped"
        # or 200/OK. Blocks CICD-SEC-1 fake-pass per
        #   https://owasp.org/www-project-top-10-ci-cd-security-risks/
        #   https://about.codecov.io/apr-2021-post-mortem/
        if os.environ.get("HERMES_AGENT_RUN_PYTEST") == "1" and tests_dir.exists():
            workers_env = os.environ.get("HERMES_AGENT_PYTEST_WORKERS", "4").strip()
            diagnostic_mode = os.environ.get("HERMES_AGENT_DIAGNOSTIC", "").strip() == "1"
            if workers_env != "auto":
                try:
                    parsed_workers = int(workers_env)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"HERMES_AGENT_PYTEST_WORKERS must be 'auto' or a positive "
                            f"integer; got {workers_env!r}."
                        ),
                    ) from exc
                if parsed_workers < 0:
                    raise HTTPException(
                        status_code=400,
                        detail="HERMES_AGENT_PYTEST_WORKERS must be 'auto' or a positive integer.",
                    )
                if not diagnostic_mode and parsed_workers < 2:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "HERMES_AGENT_PYTEST_WORKERS<2 disables xdist isolation; "
                            "set HERMES_AGENT_DIAGNOSTIC=1 to override in triage."
                        ),
                    )
            maxfail = "5" if diagnostic_mode else "1"
            pytest_args = [
                "python",
                "-m",
                "pytest",
                str(tests_dir),
                "-m",
                "not integration",
                "--ignore=tests/integration",
                "--ignore=tests/e2e",
                f"--maxfail={maxfail}",
                "-q",
                "-n",
                workers_env,
            ]
            checks.append(
                _check_external(repo, "python pytest non-integration", pytest_args, timeout=600)
            )
        elif tests_dir.exists():
            checks.append(
                {
                    "name": "python pytest non-integration",
                    "status": "fail",
                    "output": (
                        "REQUIRES_CONFIRMATION: HERMES_AGENT_RUN_PYTEST not set to '1'. "
                        "Pytest gate cannot certify update without explicit opt-in. "
                        "Re-run with HERMES_AGENT_RUN_PYTEST=1 (default workers=4) to certify, "
                        "or set HERMES_AGENT_DIAGNOSTIC=1 for triage mode."
                    ),
                }
            )
    return checks


def _check_command(
    repo: Path, name: str, args: list[str], expect_returncode: int = 0
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo, text=True, capture_output=True, timeout=30, check=False
        )
        output = redact_text((result.stdout or result.stderr).strip())[:800]
        if name == "git status" and result.returncode == expect_returncode and output:
            return {"name": name, "status": "fail", "output": output}
        return {
            "name": name,
            "status": "pass" if result.returncode == expect_returncode else "fail",
            "output": output,
        }
    except Exception as exc:
        return {"name": name, "status": "fail", "output": redact_text(str(exc))}


def _check_external(repo: Path, name: str, args: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        executable = shutil.which(args[0]) or args[0]
        result = subprocess.run(
            [executable, *args[1:]],
            cwd=repo,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "name": name,
            "status": "pass" if result.returncode == 0 else "fail",
            "output": redact_text((result.stdout or result.stderr).strip())[:800],
        }
    except Exception as exc:
        return {"name": name, "status": "fail", "output": redact_text(str(exc))}


def _run_git(repo: Path, args: list[str], timeout: int = 30) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, timeout=timeout, check=False
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail=f"git {' '.join(args)} failed: {redact_text((result.stderr or result.stdout).strip())}",
        )
    return result.stdout


def _run_git_optional(repo: Path, args: list[str]) -> str | None:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, timeout=30, check=False
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _tag_key(tag: str) -> tuple[int, int, int]:
    match = TAG_RE.match(tag)
    if not match:
        return (0, 0, 0)
    return (int(match.group("year")), int(match.group("month")), int(match.group("day")))


def _auto_repair_to_backup(
    repo: Path, backup: dict[str, Any] | None, actor: str, *, failed_tag: str
) -> dict[str, Any]:
    target = (
        (backup or {}).get("tag") or (backup or {}).get("branch") or (backup or {}).get("commit")
    )
    if not target:
        return {
            "attempted": False,
            "rolled_back": False,
            "failed_tag": failed_tag,
            "reason": "No backup target was available for automatic rollback.",
        }
    try:
        _run_git(repo, ["checkout", "--detach", str(target)], timeout=120)
        checks = _run_update_checks(repo)
        rolled_back = all(item.get("status") == "pass" for item in checks)
        repair = {
            "attempted": True,
            "rolled_back": rolled_back,
            "failed_tag": failed_tag,
            "target": target,
            "checks": checks,
        }
    except HTTPException as exc:
        repair = {
            "attempted": True,
            "rolled_back": False,
            "failed_tag": failed_tag,
            "target": target,
            "reason": redact_text(str(exc.detail)),
        }
    _append_proof_event("hermes_agent_update_auto_repair", actor, _proof_summary(repair))
    return repair


def _append_proof_event(event_type: str, source_agent: str, payload: dict[str, Any]) -> None:
    # Wave 2 P2-6 (2026-05-09): every persisted proof event carries the
    # active Hermes Agent version + upstream tag so post-promotion
    # forensic queries can attribute behavior to v0.12 (v2026.4.30) vs
    # v0.13 (v2026.5.7). Provenance basis: NIST SP 800-92 §4 (log
    # generation/storage) + OpenTelemetry resource attribute
    # ``service.version``. See services/proof_helpers.py for the merge.
    enriched = attach_version_fields(payload)
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (new_id(), event_type, source_agent, as_json(enriched)),
    )


def _proof_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep updater proof small: no full logs, no secrets, only gate verdicts and refs."""

    def summarize_check(check: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": check.get("name"),
            "status": check.get("status"),
            "output_head": redact_text(str(check.get("output") or ""))[:180],
        }

    summary = dict(payload)
    if "steps" in summary and isinstance(summary["steps"], list):
        summary["steps"] = [
            {
                "tag": step.get("tag"),
                "ok": step.get("ok"),
                "checks": [
                    summarize_check(check)
                    for check in step.get("checks", [])
                    if isinstance(check, dict)
                ],
            }
            for step in summary["steps"]
            if isinstance(step, dict)
        ]
    if "checks" in summary and isinstance(summary["checks"], list):
        summary["checks"] = [
            summarize_check(check) for check in summary["checks"] if isinstance(check, dict)
        ]
    if "backup" in summary and isinstance(summary["backup"], dict):
        backup = summary["backup"]
        summary["backup"] = {
            "backup_id": backup.get("backup_id"),
            "tag": backup.get("tag"),
            "branch": backup.get("branch"),
            "commit": backup.get("commit"),
            "dirty": backup.get("dirty"),
            "bundle_path": backup.get("bundle_path"),
            "dirty_zip_path": backup.get("dirty_zip_path"),
        }
    if "latest_backup" in summary and isinstance(summary["latest_backup"], dict):
        latest_backup = summary["latest_backup"]
        summary["latest_backup"] = {
            "backup_id": latest_backup.get("backup_id"),
            "tag": latest_backup.get("tag"),
            "commit": latest_backup.get("commit"),
            "dirty": latest_backup.get("dirty"),
        }
    if "current" in summary and isinstance(summary["current"], dict):
        current = summary["current"]
        summary["current"] = {
            "repo_ready": current.get("repo_ready"),
            "commit": current.get("commit"),
            "exact_tag": current.get("exact_tag"),
            "nearest_tag": current.get("nearest_tag"),
            "branch": current.get("branch"),
            "dirty": current.get("dirty"),
        }
    return summary
