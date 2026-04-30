"""Integration smoke test: real round-trip against a local Ollama backend.

Skipped automatically when Ollama is not reachable on 127.0.0.1:11434.
"""

from __future__ import annotations

import os

import pytest


def _ollama_reachable() -> bool:
    try:
        import httpx

        with httpx.Client(timeout=2.0) as c:
            r = c.get("http://127.0.0.1:11434/api/tags")
            return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama not running on 127.0.0.1:11434")
def test_multi_agent_loop_against_local_ollama():
    import httpx

    with httpx.Client(timeout=5.0) as c:
        models = [
            m["name"] for m in c.get("http://127.0.0.1:11434/api/tags").json().get("models", [])
        ]
    assert models, "Ollama is up but has no models pulled"

    os.environ["HERMES3D_LLM_PROVIDER"] = "ollama"
    os.environ["HERMES3D_LLM_MODEL"] = models[0]
    os.environ.setdefault("HERMES3D_LLM_TIMEOUT", "120")

    from hermes3d.core.agents.multi_agent import MultiAgentLoop

    loop = MultiAgentLoop()
    res = loop.run({"goal": "Briefly describe printability of a 50mm cube in PLA"})
    assert res.outcome in ("ok", "partial")
    assert res.rounds, "expected at least one round captured"
    if res.outcome == "ok":
        assert res.final_draft and res.final_draft.strip()
    for r in res.rounds:
        assert r.prompt
        assert r.response or r.error
