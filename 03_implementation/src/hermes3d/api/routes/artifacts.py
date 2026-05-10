from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from hermes3d.api.routes._common import execute, new_id, row, rows
from hermes3d.db.init import DB_PATH

router = APIRouter()

# ---------------------------------------------------------------------------
# Proof-bundle discovery endpoints (Lane 15 — H3D-CLAUDE-ARTIFACTS-PROOF)
# ---------------------------------------------------------------------------

# Resolve proof/ directory relative to this source file's repo root.
# Walks up from routes/ → api/ → hermes3d/ → src/ → 03_implementation/ → proof/
_ROUTES_DIR = Path(__file__).parent
_PROOF_DIR = _ROUTES_DIR.parents[3] / "proof"


def _scan_proof_dir() -> list[dict]:
    """Return a list of proof file metadata by scanning the proof/ directory tree."""
    if not _PROOF_DIR.exists():
        return []
    entries: list[dict] = []
    for root, _dirs, files in os.walk(_PROOF_DIR):
        for fname in sorted(files):
            fpath = Path(root) / fname
            rel = fpath.relative_to(_PROOF_DIR).as_posix()
            stat = fpath.stat()
            entries.append(
                {
                    "filename": rel,
                    "size_bytes": stat.st_size,
                    "modified_utc": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "type": fpath.suffix.lstrip(".") or "file",
                }
            )
    entries.sort(key=lambda e: e["filename"])
    return entries


@router.get("/api/artifacts/list")
def list_proof_files() -> dict:
    """Return all proof bundle files from 03_implementation/proof/."""
    files = _scan_proof_dir()
    return {
        "proof_dir": str(_PROOF_DIR),
        "file_count": len(files),
        "total_size_bytes": sum(f["size_bytes"] for f in files),
        "files": files,
    }


@router.get("/api/artifacts/proof/{filename:path}")
def get_proof_file(filename: str) -> FileResponse:
    """Serve a single proof file from 03_implementation/proof/ by relative path."""
    # Prevent path traversal
    target = (_PROOF_DIR / filename).resolve()
    try:
        target.relative_to(_PROOF_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid proof file path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"proof file not found: {filename}")
    return FileResponse(str(target))


@router.get("/api/artifacts")
def list_artifacts(
    job_id: str | None = None, grouped: str | None = None
) -> list[dict] | dict[str, list[dict]]:
    data = rows(
        "SELECT * FROM artifacts WHERE (? IS NULL OR job_id = ?) ORDER BY created_at DESC",
        (job_id, job_id),
    )
    if grouped == "job":
        grouped_data: dict[str, list[dict]] = {}
        for item in data:
            grouped_data.setdefault(item.get("job_id") or "unassigned", []).append(item)
        return grouped_data
    return data


@router.post("/api/artifacts", status_code=201)
async def upload_artifact(request: Request) -> dict:
    body = await request.body()
    query = request.query_params
    job_id = query.get("job_id")
    evidence_type = query.get("evidence_type", "model_evidence")
    stage = query.get("stage", "INTAKE")
    agent = query.get("agent")
    gate = query.get("gate")
    label = query.get("label")
    notes = query.get("notes", "")
    if job_id and not row("SELECT id FROM jobs WHERE id = ?", (job_id,)):
        raise HTTPException(status_code=404, detail="job not found for artifact upload")
    artifact_id = new_id()
    storage = DB_PATH.parent / "artifacts"
    storage.mkdir(parents=True, exist_ok=True)
    target = storage / f"{artifact_id}_artifact.bin"
    target.write_bytes(body)
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            job_id,
            evidence_type,
            agent,
            stage,
            gate,
            label,
            str(target),
            len(body),
            notes,
        ),
    )
    return row("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)) or {}


@router.get("/api/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str) -> FileResponse:
    artifact = row("SELECT * FROM artifacts WHERE id = ?", (artifact_id,))
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(artifact["file_path"])
