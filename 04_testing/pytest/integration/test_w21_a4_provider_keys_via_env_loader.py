"""W21-A4 MVP-1 — integration test that env_loader hydrates provider keys.

Mission: prove that writing a temp .env with MINIMAX_API_KEY+DEEPSEEK_API_KEY,
pointing HERMES3D_ENV_FILES at it, and importing the FastAPI app makes the
/api/agents/health endpoint report ``key_present: true`` for both providers.

This is the smoking-gun proof that the audit's MVP-1 fix actually unblocks
the keys. If this passes on a clean Python process, we know operator
restart of the backend will pick up G:\\private\\.env automatically.

Lag-protection: TestClient is synchronous — no sleep loops, no race risk.
The test waits on TestClient boot (already deterministic) and reads the
response directly.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def isolated_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Spin up a fresh FastAPI app with a temp .env + clean SQLite.

    The fixture force-reloads ``hermes3d.api.app`` so the module-level
    ``_hydrate_env()`` call re-runs against the temp .env. This proves the
    contract end-to-end: write a file, set HERMES3D_ENV_FILES, restart the
    process — and the keys become visible to the route handlers.
    """
    # 1. Write the temp .env with sentinel keys.
    env_path = tmp_path / "private.env"
    env_path.write_text(
        "MINIMAX_API_KEY=sentinel_minimax_key_for_test\n"
        "DEEPSEEK_API_KEY=sentinel_deepseek_key_for_test\n",
        encoding="utf-8",
    )

    # 2. Clean any pre-existing env vars so the file is the only source.
    for key in ("MINIMAX_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HERMES3D_ENV_FILES", str(env_path))

    # 3. Use a temp SQLite DB so jobs/events don't bleed into other tests.
    db_path = tmp_path / "hermes3d.db"
    # Force-reload the modules in the right order so create_gui_app
    # picks up the new HERMES3D_ENV_FILES AND a fresh DB path.
    for mod_name in list(sys.modules):
        if mod_name.startswith("hermes3d.api.app") or mod_name.startswith("hermes3d.api.routes"):
            sys.modules.pop(mod_name, None)
    sys.modules.pop("hermes3d.config.env_loader", None)
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    importlib.import_module("hermes3d.config.env_loader")
    app_mod = importlib.import_module("hermes3d.api.app")
    return TestClient(app_mod.create_gui_app())


def test_minimax_key_present_after_env_loader_runs(isolated_backend: TestClient) -> None:
    """``/api/agents/health`` must report ``minimax.key_present: true`` once
    HERMES3D_ENV_FILES points at a .env containing ``MINIMAX_API_KEY``."""
    resp = isolated_backend.get("/api/agents/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    minimax = body.get("providers", {}).get("minimax", {})
    assert minimax.get("key_present") is True, (
        f"BROKEN_BACKEND: MINIMAX_API_KEY in .env but health says "
        f"key_present={minimax.get('key_present')!r}; full minimax block={minimax!r}"
    )


def test_deepseek_key_present_after_env_loader_runs(isolated_backend: TestClient) -> None:
    """Same contract for DeepSeek."""
    resp = isolated_backend.get("/api/agents/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    deepseek = body.get("providers", {}).get("deepseek", {})
    assert deepseek.get("key_present") is True, (
        f"BROKEN_BACKEND: DEEPSEEK_API_KEY in .env but health says "
        f"key_present={deepseek.get('key_present')!r}; full deepseek block={deepseek!r}"
    )


def test_minimax_NOT_treated_as_lm_studio(isolated_backend: TestClient) -> None:
    """Critical W18 rule: LM Studio is NOT MiniMax. They must be distinct
    entries in the provider list with distinct ``kind``."""
    body = isolated_backend.get("/api/agents/health").json()
    providers = body.get("providers", {})
    assert "minimax" in providers
    assert "lm_studio" in providers
    # MiniMax is a live_remote provider; LM Studio is a local fallback.
    assert providers["minimax"].get("kind") == "live_remote"
    # They must not share the same key (key_present semantics differ).
    assert providers["minimax"].get("model") != providers["lm_studio"].get("model")
