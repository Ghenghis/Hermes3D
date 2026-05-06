from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from hermes3d.api.routes._common import execute, new_id, row, rows
from hermes3d.db.init import DB_PATH

router = APIRouter()


@router.get("/api/artifacts")
def list_artifacts(job_id: str | None = None, grouped: str | None = None) -> list[dict] | dict[str, list[dict]]:
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
        (artifact_id, job_id, evidence_type, agent, stage, gate, label, str(target), len(body), notes),
    )
    return row("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)) or {}


@router.get("/api/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str) -> FileResponse:
    artifact = row("SELECT * FROM artifacts WHERE id = ?", (artifact_id,))
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(artifact["file_path"])
