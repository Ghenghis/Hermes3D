from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from hermes3d.api.routes._common import execute, new_id, row, rows
from hermes3d.db.init import DB_PATH

router = APIRouter()

# ---------------------------------------------------------------------------
# W21-MVP-4 — artifact lineage
# ---------------------------------------------------------------------------
#
# Hermes3D records lineage by storing parent/child artifact IDs inside the
# ``artifacts.notes`` JSON column. The shape is established in
# ``api/routes/design.py`` and ``api/routes/generation.py``:
#
#   mesh row's notes:        ``proof_artifact_id``    (mesh → proof)
#   proof_report row's notes:``mesh_artifact_id``     (proof → mesh)
#   thumbnail row's notes:   ``mesh_artifact_id``     (thumbnail → mesh)
#   generation mesh notes:   ``reference_artifact_id``(mesh → upstream logo/image)
#
# The set below pins the keys we recognise. Adding a new lineage relation
# means: (a) record it in notes inside the producer, (b) add it here, and
# (c) extend the lineage tests.
_LINEAGE_KEYS: tuple[str, ...] = (
    "mesh_artifact_id",
    "proof_artifact_id",
    "thumbnail_artifact_id",
    "reference_artifact_id",
)


def _parse_notes(notes_raw: Any) -> dict[str, Any]:
    """Defensive JSON decode of an ``artifacts.notes`` blob.

    Older rows (reconciler-inserted) may store either a JSON object, a
    free-form string, or an empty string. We must never raise from a
    parse failure — the row simply contributes no lineage edges.
    """
    if not notes_raw:
        return {}
    if isinstance(notes_raw, dict):
        return notes_raw
    if isinstance(notes_raw, str):
        try:
            parsed = json.loads(notes_raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _trim_for_lineage(artifact_row: dict[str, Any], via: str | None) -> dict[str, Any]:
    """Produce the lineage-projection of an artifact row.

    The lineage endpoint returns a compact view per related artifact so
    the UI can render parent/child cards without re-fetching: id,
    evidence_type, label, file_path, created_at, plus the ``via`` field
    that names the key in notes that linked us.
    """
    return {
        "id": artifact_row["id"],
        "evidence_type": artifact_row.get("evidence_type"),
        "label": artifact_row.get("label"),
        "file_path": artifact_row.get("file_path"),
        "created_at": artifact_row.get("created_at"),
        "via": via,
    }


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


@router.get("/api/artifacts/{artifact_id}/lineage")
def artifact_lineage(artifact_id: str) -> dict[str, Any]:
    """Return the parents and children of one artifact.

    Lineage is encoded inside ``artifacts.notes`` JSON (see
    ``_LINEAGE_KEYS``). The endpoint walks one step in each direction:

      * **parents**  — every artifact whose id appears under one of
        ``_LINEAGE_KEYS`` inside *this* row's notes. The ``via`` field
        names the key (e.g. ``mesh_artifact_id``).
      * **children** — every artifact whose notes mention *this* id
        under one of ``_LINEAGE_KEYS``. Detected with SQL LIKE so the
        scan is bounded even on a 10k-row table.

    Returns 404 if the artifact does not exist.

    The response is intentionally compact (id + evidence_type + label +
    file_path + created_at per related row) so the UI can render a
    lineage panel without fanning out to N follow-up requests.
    """
    artifact = row("SELECT * FROM artifacts WHERE id = ?", (artifact_id,))
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")

    # Parents — read THIS row's notes and resolve every recognised id.
    parents: list[dict[str, Any]] = []
    seen_parent_ids: set[str] = set()
    notes = _parse_notes(artifact.get("notes"))
    for key in _LINEAGE_KEYS:
        parent_id = notes.get(key)
        if not isinstance(parent_id, str) or not parent_id:
            continue
        if parent_id == artifact_id or parent_id in seen_parent_ids:
            continue
        parent_row = row("SELECT * FROM artifacts WHERE id = ?", (parent_id,))
        if parent_row is None:
            # Lineage edge points to a row that was reaped or never
            # existed. Emit a sentinel so the UI can show "missing
            # parent" rather than silently drop the link.
            parents.append(
                {
                    "id": parent_id,
                    "evidence_type": None,
                    "label": None,
                    "file_path": None,
                    "created_at": None,
                    "via": key,
                    "missing": True,
                }
            )
        else:
            parents.append(_trim_for_lineage(parent_row, via=key))
        seen_parent_ids.add(parent_id)

    # Children — find every other row whose notes mention this id under
    # any lineage key. SQL LIKE on the JSON column is bounded, but we
    # still need to JSON-parse to distinguish the key path.
    candidates = rows(
        "SELECT * FROM artifacts WHERE id != ? AND notes LIKE ? ORDER BY created_at",
        (artifact_id, f"%{artifact_id}%"),
    )
    children: list[dict[str, Any]] = []
    for cand in candidates:
        cand_notes = _parse_notes(cand.get("notes"))
        for key in _LINEAGE_KEYS:
            if cand_notes.get(key) == artifact_id:
                children.append(_trim_for_lineage(cand, via=key))
                break  # one edge per child is enough

    return {
        "artifact": dict(artifact),
        "parents": parents,
        "children": children,
        "lineage_keys": list(_LINEAGE_KEYS),
    }
