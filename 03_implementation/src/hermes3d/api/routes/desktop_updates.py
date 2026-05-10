from __future__ import annotations

import hashlib
import hmac
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
from hermes3d.services.proof_helpers import attach_version_fields

router = APIRouter()

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[4]
BACKUP_ROOT = IMPLEMENTATION_ROOT / "var" / "hermes_desktop_backups"
DOWNLOAD_ROOT = IMPLEMENTATION_ROOT / "var" / "hermes_desktop_downloads"
DEFAULT_CHECKOUT = Path(os.environ.get("HERMES_DESKTOP_CHECKOUT", "G:/Github/apps/hermes-desktop-main"))
UPSTREAM_URL = os.environ.get("HERMES_DESKTOP_UPSTREAM_URL", "https://github.com/fathah/hermes-desktop.git")
LATEST_RELEASE_API = "https://api.github.com/repos/fathah/hermes-desktop/releases/latest"
TAG_RE = re.compile(r"^v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
SECRET_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+|([?&](?:token|key|api_key|access_token)=)[^&\s]+|([A-Za-z0-9_]*KEY=)[^\s]+")


class BackupRequest(BaseModel):
    note: str | None = None


class DownloadRequest(BaseModel):
    asset_name: str | None = None


@router.get("/api/desktop/update/status")
def desktop_update_status() -> dict[str, Any]:
    checkout = _checkout_path()
    source = _source_state(checkout)
    latest = _latest_release()
    local_version = source.get("package_version")
    latest_version = _version_from_tag(latest.get("tag"))
    outdated = bool(local_version and latest_version and _semver_key(local_version) < _semver_key(latest_version))
    payload = {
        "repo_url": UPSTREAM_URL,
        "checkout_path": str(checkout),
        "source_ready": source["source_ready"],
        "git_ready": source["git_ready"],
        "current": source,
        "latest_release": latest,
        "outdated": outdated,
        "strategy": "download_windows_installer_record_sha256; source checkout updates remain unsupported until staged update and rollback routes exist",
        "installer_download_supported": bool(latest.get("installer_asset")),
        "installer_verification_supported": bool((latest.get("installer_asset") or {}).get("digest")) if isinstance(latest.get("installer_asset"), dict) else False,
        "source_update_supported": False,
        "backup_available": _latest_backup() is not None,
        "latest_backup": _latest_backup(),
    }
    _append_proof_event("hermes_desktop_update_status", "hermes3d-updater", _proof_summary(payload))
    return payload


@router.post("/api/desktop/update/backup", status_code=201)
def desktop_backup(body: BackupRequest | None = None) -> dict[str, Any]:
    backup = _create_backup(_checkout_path(), note=(body.note if body else None) or "manual Hermes Desktop pre-update backup")
    _append_proof_event("hermes_desktop_backup_created", "hermes3d-updater", _proof_summary({"backup": backup}))
    return backup


@router.post("/api/desktop/update/download", status_code=201)
def desktop_download(body: DownloadRequest | None = None) -> dict[str, Any]:
    latest = _latest_release()
    assets = latest.get("assets") if isinstance(latest.get("assets"), list) else []
    wanted = body.asset_name if body else None
    asset = next((item for item in assets if item.get("name") == wanted), None) if wanted else latest.get("installer_asset")
    if not isinstance(asset, dict):
        raise HTTPException(status_code=409, detail="No downloadable Hermes Desktop installer asset was discovered in the latest release.")
    url = asset.get("browser_download_url")
    name = asset.get("name")
    if not isinstance(url, str) or not isinstance(name, str):
        raise HTTPException(status_code=409, detail="Latest release asset was missing a download URL.")
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    target = DOWNLOAD_ROOT / _safe_filename(name)
    request = urllib.request.Request(url, headers={"User-Agent": "Hermes3D-Desktop-Updater/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    digest = _sha256(target)
    expected_digest = _digest_value(asset.get("digest"))
    verification_status = "sha256_recorded_only"
    if expected_digest:
        verification_status = "sha256_verified_github_release_digest" if hmac_compare_digest(digest, expected_digest) else "sha256_mismatch"
        if verification_status == "sha256_mismatch":
            raise HTTPException(
                status_code=502,
                detail={
                    "status": "blocked",
                    "reason": "Downloaded Hermes Desktop installer SHA-256 did not match the GitHub release asset digest.",
                    "asset_name": name,
                    "sha256": digest,
                    "expected_sha256": expected_digest,
                },
            )
    payload = {
        "downloaded": True,
        "asset_name": name,
        "path": str(target),
        "size_bytes": target.stat().st_size,
        "sha256": digest,
        "expected_sha256": expected_digest,
        "verification_status": verification_status,
        "release": latest,
        "next_step": "Installer digest is verified against GitHub release metadata when expected_sha256 is present. Hermes3D does not silently execute installers.",
    }
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("hermes_desktop.update.latest_download", json.dumps(payload)),
    )
    _append_proof_event("hermes_desktop_installer_downloaded", "hermes3d-updater", _proof_summary(payload))
    return payload


def _checkout_path() -> Path:
    return DEFAULT_CHECKOUT


def _source_state(path: Path) -> dict[str, Any]:
    package = path / "package.json"
    package_version = None
    package_name = None
    if package.exists():
        try:
            parsed = json.loads(package.read_text(encoding="utf-8"))
            package_version = parsed.get("version")
            package_name = parsed.get("name")
        except json.JSONDecodeError:
            pass
    git_ready = (path / ".git").exists()
    commit = _run_git_optional(path, ["rev-parse", "--short=12", "HEAD"]) if git_ready else None
    exact_tag = _run_git_optional(path, ["describe", "--tags", "--exact-match"]) if git_ready else None
    nearest_tag = _run_git_optional(path, ["describe", "--tags", "--abbrev=0"]) if git_ready else None
    dirty = bool((_run_git_optional(path, ["status", "--porcelain=v1"]) or "").strip()) if git_ready else None
    return {
        "source_ready": package.exists(),
        "git_ready": git_ready,
        "reason": None if package.exists() else f"Hermes Desktop source path does not contain package.json: {path}",
        "package_name": package_name,
        "package_version": package_version,
        "commit": commit,
        "exact_tag": exact_tag,
        "nearest_tag": nearest_tag,
        "dirty": dirty,
    }


def _latest_release() -> dict[str, Any]:
    try:
        request = urllib.request.Request(LATEST_RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "Hermes3D-Desktop-Updater"})
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"tag": None, "name": None, "source": "github_releases_api", "api_warning": _redact(str(exc)), "assets": []}
    assets = [
        {
            "name": asset.get("name"),
            "size": asset.get("size"),
            "digest": asset.get("digest"),
            "browser_download_url": asset.get("browser_download_url"),
            "content_type": asset.get("content_type"),
        }
        for asset in payload.get("assets", [])
        if isinstance(asset, dict)
    ]
    installer = next((asset for asset in assets if str(asset.get("name") or "").lower().endswith(".exe")), None)
    return {
        "tag": payload.get("tag_name"),
        "name": payload.get("name") or payload.get("tag_name"),
        "published_at": payload.get("published_at"),
        "html_url": payload.get("html_url"),
        "source": "github_releases_api",
        "assets": assets,
        "installer_asset": installer,
    }


def _create_backup(path: Path, note: str) -> dict[str, Any]:
    state = _source_state(path)
    if not state["source_ready"]:
        raise HTTPException(status_code=409, detail=state["reason"])
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    version = str(state.get("exact_tag") or state.get("package_version") or "unknown").replace("/", "_")
    backup_id = f"{stamp}_{version}"
    meta_path = BACKUP_ROOT / f"{backup_id}.json"
    if state["git_ready"]:
        bundle_path = BACKUP_ROOT / f"{backup_id}.bundle"
        _run_git(path, ["bundle", "create", str(bundle_path), "--all"], timeout=180)
        archive_path = None
    else:
        bundle_path = None
        archive_path = BACKUP_ROOT / f"{backup_id}.source.zip"
        _zip_source_snapshot(path, archive_path)
    metadata = {
        "backup_id": backup_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
        "checkout_path": str(path),
        "package_version": state.get("package_version"),
        "tag": state.get("exact_tag") or state.get("nearest_tag"),
        "commit": state.get("commit"),
        "git_ready": state["git_ready"],
        "bundle_path": str(bundle_path) if bundle_path else None,
        "source_zip_path": str(archive_path) if archive_path else None,
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("hermes_desktop.update.latest_backup", json.dumps(metadata)),
    )
    return metadata


def _zip_source_snapshot(root: Path, target: Path) -> None:
    excluded_dirs = {".git", "node_modules", "out", "dist", "release", ".vite", ".turbo"}
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            rel = path.relative_to(root)
            if any(part in excluded_dirs for part in rel.parts):
                continue
            if path.is_file():
                archive.write(path, rel)


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


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if value.lower().startswith("sha256:"):
        candidate = value.split(":", 1)[1].strip().lower()
    else:
        candidate = value.strip().lower()
    return candidate if re.fullmatch(r"[0-9a-f]{64}", candidate) else None


def hmac_compare_digest(left: str, right: str) -> bool:
    return hmac.compare_digest(left.lower(), right.lower())


def _version_from_tag(tag: Any) -> str | None:
    if not isinstance(tag, str):
        return None
    return tag[1:] if tag.startswith("v") else tag


def _semver_key(version: str) -> tuple[int, int, int]:
    match = TAG_RE.match(f"v{version}" if not version.startswith("v") else version)
    if not match:
        return (0, 0, 0)
    return (int(match.group("major")), int(match.group("minor")), int(match.group("patch")))


def _run_git(path: Path, args: list[str], timeout: int = 30) -> str:
    result = subprocess.run(["git", *args], cwd=path, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise HTTPException(status_code=502, detail=f"git {' '.join(args)} failed: {_redact((result.stderr or result.stdout).strip())}")
    return result.stdout


def _run_git_optional(path: Path, args: list[str]) -> str | None:
    result = subprocess.run(["git", *args], cwd=path, text=True, capture_output=True, timeout=30, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _append_proof_event(event_type: str, source_agent: str, payload: dict[str, Any]) -> None:
    # Wave 2 P2-6 (2026-05-09): version-tag every persisted proof
    # event. Mirrors agent_updates.py / jobs.py call sites; see
    # services/proof_helpers.py for the merge contract and the
    # NIST SP 800-92 §4 + OpenTelemetry ``service.version`` provenance
    # basis. The desktop updater records its own checkout via
    # HERMES_DESKTOP_CHECKOUT, but the active *Hermes Agent* version
    # is what the audit chain attributes — this row tracks BOTH because
    # desktop releases coordinate with the agent runtime.
    enriched = attach_version_fields(payload)
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (new_id(), event_type, source_agent, as_json(enriched)),
    )


def _proof_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    if "latest_release" in summary and isinstance(summary["latest_release"], dict):
        latest = summary["latest_release"]
        summary["latest_release"] = {
            "tag": latest.get("tag"),
            "name": latest.get("name"),
            "published_at": latest.get("published_at"),
            "html_url": latest.get("html_url"),
            "installer_asset": (latest.get("installer_asset") or {}).get("name") if isinstance(latest.get("installer_asset"), dict) else None,
        }
    if "backup" in summary and isinstance(summary["backup"], dict):
        backup = summary["backup"]
        summary["backup"] = {
            "backup_id": backup.get("backup_id"),
            "package_version": backup.get("package_version"),
            "tag": backup.get("tag"),
            "commit": backup.get("commit"),
            "git_ready": backup.get("git_ready"),
        }
    if "current" in summary and isinstance(summary["current"], dict):
        current = summary["current"]
        summary["current"] = {
            "source_ready": current.get("source_ready"),
            "git_ready": current.get("git_ready"),
            "package_version": current.get("package_version"),
            "commit": current.get("commit"),
            "exact_tag": current.get("exact_tag"),
            "nearest_tag": current.get("nearest_tag"),
            "dirty": current.get("dirty"),
        }
    return summary


def _redact(value: str) -> str:
    return SECRET_RE.sub(lambda match: f"{match.group(1) or match.group(2) or match.group(3) or ''}[REDACTED]", value)
