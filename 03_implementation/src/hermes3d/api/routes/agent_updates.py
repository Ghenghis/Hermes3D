from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id

router = APIRouter()

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[4]
BACKUP_ROOT = IMPLEMENTATION_ROOT / "var" / "hermes_agent_backups"
DEFAULT_CHECKOUT = Path(os.environ.get("HERMES_AGENT_CHECKOUT", "G:/Github/hermes-agent-fresh"))
UPSTREAM_URL = os.environ.get("HERMES_AGENT_UPSTREAM_URL", "https://github.com/NousResearch/Hermes-Agent.git")
LATEST_RELEASE_API = "https://api.github.com/repos/NousResearch/hermes-agent/releases/latest"
RELEASES_API = "https://api.github.com/repos/NousResearch/hermes-agent/releases?per_page=100"
TAG_RE = re.compile(r"^v(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})$")
BACKUP_ID_RE = re.compile(r"^[A-Za-z0-9._-]{12,96}$")
SECRET_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+|([?&](?:token|key|api_key|access_token)=)[^&\s]+|([A-Za-z0-9_]*KEY=)[^\s]+")


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


@router.get("/api/agents/update/status")
def update_status() -> dict[str, Any]:
    repo = _repo_path()
    state = _repo_state(repo)
    tags = _remote_release_tags(repo)
    latest = _latest_release(tags)
    if isinstance(latest.get("tag"), str) and latest["tag"] not in tags:
        tags = sorted([*tags, latest["tag"]], key=_tag_key)
    current_tag = state.get("exact_tag") or state.get("nearest_tag")
    pending = _pending_tags(tags, current_tag, latest.get("tag"))
    backup = _latest_backup()
    payload = {
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
    _append_proof_event("hermes_agent_update_status", "hermes3d-updater", _proof_summary(payload))
    return payload


@router.post("/api/agents/update/backup", status_code=201)
def create_update_backup(body: BackupRequest | None = None) -> dict[str, Any]:
    backup = _create_backup(_repo_path(), note=(body.note if body else None) or "manual Hermes Agent pre-update backup")
    _append_proof_event("hermes_agent_backup_created", "hermes3d-updater", _proof_summary({"backup": backup}))
    return backup


@router.post("/api/agents/update/staged")
def staged_update(body: StagedUpdateRequest) -> dict[str, Any]:
    repo = _repo_path()
    state = _repo_state(repo)
    if not state["repo_ready"]:
        raise HTTPException(status_code=409, detail=state["reason"])
    if body.create_backup is not True:
        raise HTTPException(status_code=400, detail="A pre-update backup is required before every Hermes Agent staged update.")
    _ensure_remote(repo)
    _run_git(repo, ["fetch", "--tags", "upstream"], timeout=120)
    tags = _remote_release_tags(repo)
    latest = _latest_release(tags)
    if isinstance(latest.get("tag"), str) and latest["tag"] not in tags:
        tags = sorted([*tags, latest["tag"]], key=_tag_key)
    target = body.target_tag or latest.get("tag")
    if not target:
        raise HTTPException(status_code=409, detail="No release target was discovered from the GitHub Releases API.")
    current_tag = state.get("exact_tag") or state.get("nearest_tag")
    pending = _pending_tags(tags, current_tag, target)
    if not pending:
        payload = {"updated": False, "status": "already_current", "current": _repo_state(repo), "latest_release": latest, "steps": []}
        _append_proof_event("hermes_agent_update_skipped", body.actor, _proof_summary(payload))
        return payload
    steps = pending[: max(1, min(body.max_steps, 10))]
    backup = _create_backup(repo, note=f"automatic backup before staged update to {steps[-1]}")
    results: list[dict[str, Any]] = []
    repair: dict[str, Any] | None = None
    for tag in steps:
        # Bonus 12 finding #3 fix (PR #135): _run_git raises HTTPException(502)
        # on non-zero exit, and _run_update_checks raises HTTPException(400) for
        # bad pytest worker config. Without this guard either escapes the loop
        # without reaching _auto_repair_to_backup, leaving the repo on the
        # previous (still-unverified) tag. Surface as a structured step failure
        # and pivot to auto-repair like any other failed gate.
        try:
            _run_git(repo, ["checkout", "--detach", tag], timeout=120)
            checks = _run_update_checks(repo) if body.run_checks else [{"name": "checks", "status": "skipped", "output": "run_checks=false prevents verified update."}]
        except HTTPException as exc:
            synthetic_check = {
                "name": "git checkout to staged tag",
                "status": "fail",
                "output": _redact(str(exc.detail))[:800],
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
    status = "updated" if all_ok else "rolled_back_after_unverified_check" if has_skipped and repair and repair.get("rolled_back") else "rolled_back_after_failed_check" if repair and repair.get("rolled_back") else "stopped_on_unverified_check" if has_skipped else "stopped_on_failed_check"
    payload = {
        "updated": all_ok,
        "status": status,
        "verified": all_ok,
        "reason": None if all_ok else "One or more mandatory update gates failed or were skipped; update was not accepted as verified.",
        "backup": backup,
        "steps": results,
        "repair": repair,
        "current": final_state,
        "latest_release": latest,
        "remaining_tags": _pending_tags(tags, final_state.get("exact_tag") or final_state.get("nearest_tag"), target),
    }
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("hermes_agent.update.last_run", json.dumps({"actor": body.actor, **payload})),
    )
    _append_proof_event("hermes_agent_update_run", body.actor, _proof_summary(payload))
    return payload


@router.post("/api/agents/update/rollback")
def rollback_update(body: RollbackRequest) -> dict[str, Any]:
    repo = _repo_path()
    state = _repo_state(repo)
    if not state["repo_ready"]:
        raise HTTPException(status_code=409, detail=state["reason"])
    backup = _find_backup(body.backup_id) if body.backup_id else _latest_backup()
    if not backup:
        raise HTTPException(status_code=409, detail="Rollback requires an existing Hermes Agent backup record.")
    recorded_targets = [backup.get("tag"), backup.get("branch"), backup.get("commit")]
    target = body.tag or next((item for item in recorded_targets if item), None)
    if body.tag and body.tag not in recorded_targets:
        raise HTTPException(status_code=400, detail="Rollback target must match the selected backup's recorded tag, branch, or commit.")
    if not target:
        raise HTTPException(status_code=409, detail="No rollback tag or backup target is available.")
    _create_backup(repo, note=f"automatic backup before rollback to {target}")
    _run_git(repo, ["checkout", "--detach", str(target)], timeout=120)
    checks = _run_update_checks(repo)
    final_state = _repo_state(repo)
    ok = all(item.get("status") == "pass" for item in checks)
    payload = {"rolled_back": ok, "status": "rolled_back" if ok else "rollback_failed_checks", "target": target, "checks": checks, "current": final_state}
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("hermes_agent.update.last_rollback", json.dumps({"actor": body.actor, **payload})),
    )
    _append_proof_event("hermes_agent_update_rollback", body.actor, _proof_summary(payload))
    return payload


def _repo_path() -> Path:
    return DEFAULT_CHECKOUT


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
    del repo
    try:
        request = urllib.request.Request(RELEASES_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "Hermes3D-Agent-Updater"})
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    tags = [item.get("tag_name") for item in payload if isinstance(item, dict)]
    return sorted({tag for tag in tags if isinstance(tag, str) and TAG_RE.match(tag)}, key=_tag_key)


def _latest_release(tags: list[str]) -> dict[str, Any]:
    latest: dict[str, Any] = {"tag": None, "name": None, "source": "github_releases_api"}
    try:
        request = urllib.request.Request(LATEST_RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "Hermes3D-Agent-Updater"})
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        api_tag = payload.get("tag_name")
        if isinstance(api_tag, str) and TAG_RE.match(api_tag):
            latest.update({
                "tag": api_tag,
                "name": payload.get("name") or api_tag,
                "published_at": payload.get("published_at"),
                "html_url": payload.get("html_url"),
                "source": "github_releases_api",
            })
    except Exception as exc:
        latest["api_warning"] = _redact(str(exc))
    if latest.get("tag") is None and tags:
        latest["api_warning"] = "GitHub Releases latest endpoint unavailable; refusing to treat tags as releases."
    return latest


def _pending_tags(tags: list[str], current_tag: str | None, target_tag: str | None) -> list[str]:
    if not target_tag or target_tag not in tags:
        return []
    target_index = tags.index(target_tag)
    if current_tag in tags:
        return tags[tags.index(current_tag) + 1 : target_index + 1]
    return [target_tag]


def _create_backup(repo: Path, note: str) -> dict[str, Any]:
    state = _repo_state(repo)
    if not state["repo_ready"]:
        raise HTTPException(status_code=409, detail=state["reason"])
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_tag = str(state.get("exact_tag") or state.get("nearest_tag") or "untagged").replace("/", "_")
    backup_id = f"{stamp}_{safe_tag}_{state['commit']}"
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
        "checkout_path": str(repo),
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
    if not paths:
        return
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(repo))


def _latest_backup() -> dict[str, Any] | None:
    if not BACKUP_ROOT.exists():
        return None
    backups = sorted(BACKUP_ROOT.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not backups:
        return None
    try:
        return json.loads(backups[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
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
        checks.append(_check_external(repo, "python pyproject metadata", ["python", "-m", "pip", "--version"]))
        compile_targets = [str(path) for path in [repo / "run_agent.py", repo / "hermes_cli", repo / "gateway", repo / "agent"] if path.exists()]
        if compile_targets:
            checks.append(_check_external(repo, "python compile gate", ["python", "-m", "compileall", "-q", *compile_targets], timeout=180))
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
                "python", "-m", "pytest", str(tests_dir),
                "-m", "not integration",
                "--ignore=tests/integration",
                "--ignore=tests/e2e",
                f"--maxfail={maxfail}",
                "-q",
                "-n", workers_env,
            ]
            checks.append(_check_external(repo, "python pytest non-integration", pytest_args, timeout=600))
        elif tests_dir.exists():
            checks.append({
                "name": "python pytest non-integration",
                "status": "fail",
                "output": (
                    "REQUIRES_CONFIRMATION: HERMES_AGENT_RUN_PYTEST not set to '1'. "
                    "Pytest gate cannot certify update without explicit opt-in. "
                    "Re-run with HERMES_AGENT_RUN_PYTEST=1 (default workers=4) to certify, "
                    "or set HERMES_AGENT_DIAGNOSTIC=1 for triage mode."
                ),
            })
    return checks


def _check_command(repo: Path, name: str, args: list[str], expect_returncode: int = 0) -> dict[str, Any]:
    try:
        result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, timeout=30, check=False)
        output = _redact((result.stdout or result.stderr).strip())[:800]
        if name == "git status" and result.returncode == expect_returncode and output:
            return {"name": name, "status": "fail", "output": output}
        return {"name": name, "status": "pass" if result.returncode == expect_returncode else "fail", "output": output}
    except Exception as exc:
        return {"name": name, "status": "fail", "output": _redact(str(exc))}


def _check_external(repo: Path, name: str, args: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        executable = shutil.which(args[0]) or args[0]
        result = subprocess.run([executable, *args[1:]], cwd=repo, text=True, capture_output=True, timeout=timeout, check=False)
        return {"name": name, "status": "pass" if result.returncode == 0 else "fail", "output": _redact((result.stdout or result.stderr).strip())[:800]}
    except Exception as exc:
        return {"name": name, "status": "fail", "output": _redact(str(exc))}


def _run_git(repo: Path, args: list[str], timeout: int = 30) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise HTTPException(status_code=502, detail=f"git {' '.join(args)} failed: {_redact((result.stderr or result.stdout).strip())}")
    return result.stdout


def _run_git_optional(repo: Path, args: list[str]) -> str | None:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, timeout=30, check=False)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _tag_key(tag: str) -> tuple[int, int, int]:
    match = TAG_RE.match(tag)
    if not match:
        return (0, 0, 0)
    return (int(match.group("year")), int(match.group("month")), int(match.group("day")))


def _auto_repair_to_backup(repo: Path, backup: dict[str, Any] | None, actor: str, *, failed_tag: str) -> dict[str, Any]:
    target = (backup or {}).get("tag") or (backup or {}).get("branch") or (backup or {}).get("commit")
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
            "reason": _redact(str(exc.detail)),
        }
    _append_proof_event("hermes_agent_update_auto_repair", actor, _proof_summary(repair))
    return repair


def _append_proof_event(event_type: str, source_agent: str, payload: dict[str, Any]) -> None:
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (new_id(), event_type, source_agent, as_json(payload)),
    )


def _proof_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep updater proof small: no full logs, no secrets, only gate verdicts and refs."""
    def summarize_check(check: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": check.get("name"),
            "status": check.get("status"),
            "output_head": _redact(str(check.get("output") or ""))[:180],
        }

    summary = dict(payload)
    if "steps" in summary and isinstance(summary["steps"], list):
        summary["steps"] = [
            {
                "tag": step.get("tag"),
                "ok": step.get("ok"),
                "checks": [summarize_check(check) for check in step.get("checks", []) if isinstance(check, dict)],
            }
            for step in summary["steps"]
            if isinstance(step, dict)
        ]
    if "checks" in summary and isinstance(summary["checks"], list):
        summary["checks"] = [summarize_check(check) for check in summary["checks"] if isinstance(check, dict)]
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


def _redact(value: str) -> str:
    return SECRET_RE.sub(lambda match: f"{match.group(1) or match.group(2) or match.group(3) or ''}[REDACTED]", value)
