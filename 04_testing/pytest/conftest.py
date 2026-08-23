"""Pytest configuration: make `hermes3d` importable from 03_implementation/src/."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

# 04_testing/pytest/conftest.py -> 04_testing/pytest -> 04_testing -> repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if TYPE_CHECKING:
    import pytest

# Provider/credential env-var names that unit tests must control explicitly.
# ``env_value()`` (agent_runtime.py) and the provider adapters resolve real
# ``os.environ`` values BEFORE any dict/monkeypatch value a test supplies, by
# design (a shell/CI-provided secret should always win over a private .env
# file). That means a developer machine with real keys configured for daily
# use (MiniMax token-plan keys, MCP lock server overrides, etc.) will leak
# through unit tests that only monkeypatch a *different*, lower-priority
# name — silently pulling a real secret into an assertion diff. Call
# ``strip_provider_env(monkeypatch)`` at the top of any unit test that
# exercises provider-key or MCP-lock resolution so behaviour is identical on
# every machine, and so failures never print a real credential.
PROVIDER_SECRET_ENV_NAMES: tuple[str, ...] = (
    "MINIMAX_API_KEY",
    "MINIMAX_TOKEN_PLAN_API_KEY",
    "HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY",
    "MINIMAX_HIGHSPEED_API_KEY",
    "HERMES3D_MINIMAX_HIGHSPEED_API_KEY",
    "HERMES3D_MINIMAX_API_KEY",
    "MINIMAX_BASE_URL",
    "MINIMAX_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "MCP_LOCK_SERVER",
    "HERMES3D_MCP_SERVER",
    "MCP_LOCK_WORKSPACE",
    "HERMES3D_WORKSPACE",
    "HERMES_LOCK_WORKSPACE",
)


def strip_provider_env(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Delete every known provider/MCP-lock env var so tests are hermetic."""
    for name in PROVIDER_SECRET_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
