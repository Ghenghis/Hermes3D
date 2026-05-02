"""Provider fixture server for Phase 3.4 probe tests."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response

RESPONSES_DIR = Path(__file__).parent


def create_app(provider_id: str = "minimax", mode: str = "happy") -> FastAPI:
    responses = json.loads(
        (RESPONSES_DIR / f"{provider_id}_responses.json").read_text(encoding="utf-8")
    )
    app = FastAPI()

    @app.get("/v1/models")
    def models(response: Response) -> object:
        entry = _entry(responses, mode)
        response.status_code = int(entry.get("probe_status", 200))
        return entry.get("probe_body", {})

    @app.post("/v1/chat/completions")
    async def completions(request: Request, response: Response) -> object:
        _ = await request.json()
        entry = _entry(responses, mode)
        response.status_code = int(entry.get("completion_status", 401))
        return entry.get("completion_body", {"error": "fixture_completion_unavailable"})

    return app


def _entry(responses: dict[str, object], mode: str) -> dict[str, object]:
    entry = responses.get(mode)
    if not isinstance(entry, dict):
        raise HTTPException(status_code=404, detail=f"unknown fixture mode: {mode}")
    return entry
