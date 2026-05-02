"""Deterministic in-process LLM fixture for CP3.3-C."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from starlette.responses import JSONResponse, PlainTextResponse, Response

_RESPONSES_PATH = Path(__file__).with_name("responses.json")


def create_app(*, mode: str) -> FastAPI:
    responses = _load_responses()
    if mode not in responses:
        raise ValueError(f"unknown fixture LLM mode: {mode}")

    app = FastAPI(title="Hermes3D LLM Fixture")

    @app.post("/v1/completions")
    def complete(payload: dict[str, Any]) -> Response:
        prompt = payload.get("prompt")
        max_tokens = payload.get("max_tokens")
        if not isinstance(prompt, str) or not isinstance(max_tokens, int):
            return JSONResponse({"error": "prompt and max_tokens are required"}, status_code=400)

        fixture = responses[mode]
        body = fixture["body"]
        if fixture["content_type"] == "text/plain":
            return PlainTextResponse(str(body))
        return JSONResponse(body)

    return app


def _load_responses() -> dict[str, dict[str, object]]:
    return json.loads(_RESPONSES_PATH.read_text(encoding="utf-8"))
