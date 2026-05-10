"""Tests for service/web-app probe functions in module_runtime (I6).

All tests are non-mutating: they mock network I/O and verify probe logic
without starting any service, posting to any endpoint, or touching printers.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from hermes3d.services import module_runtime
from hermes3d.services.module_runtime import (
    SERVICE_WEB_HEALTH_MODULE_IDS,
    probe_comfyui,
    probe_fdm_monster,
    probe_fluidd,
    probe_mainsail,
    probe_manyfold,
    probe_octoprint,
    probe_octofarm,
    probe_service_web_health,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SERVICE_IDS = [
    "fluidd",
    "mainsail",
    "octoprint",
    "fdm_monster",
    "octofarm",
    "manyfold",
    "comfyui",
]

_PROBE_FNS = {
    "fluidd": probe_fluidd,
    "mainsail": probe_mainsail,
    "octoprint": probe_octoprint,
    "fdm_monster": probe_fdm_monster,
    "octofarm": probe_octofarm,
    "manyfold": probe_manyfold,
    "comfyui": probe_comfyui,
}


def _mock_http_response(body: bytes, status: int = 200) -> MagicMock:
    """Return a mock urllib response with given body and status."""
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.status = status
    mock.read.return_value = body
    return mock


def _make_env_patcher(module_id: str, url: str) -> Any:
    """Return env dict for patching so the probe sees the configured URL."""
    probe = module_runtime.runtime_probe_config(module_id)
    assert probe is not None, f"No probe config for {module_id}"
    args = [str(a) for a in (probe.get("args") or [])]
    env_name = args[0].strip() if args else f"HERMES3D_SOURCE_{module_id.upper()}_URL"
    return {env_name: url}


# ---------------------------------------------------------------------------
# SERVICE_WEB_HEALTH_MODULE_IDS contract
# ---------------------------------------------------------------------------


def test_service_web_health_module_ids_contains_all_seven() -> None:
    """All seven service IDs must be present in the frozenset."""
    expected = {"fluidd", "mainsail", "octoprint", "fdm_monster", "octofarm", "manyfold", "comfyui"}
    assert expected <= SERVICE_WEB_HEALTH_MODULE_IDS


def test_each_service_has_builtin_probe_config() -> None:
    """Every service in SERVICE_WEB_HEALTH_MODULE_IDS must have a registered probe."""
    for module_id in SERVICE_WEB_HEALTH_MODULE_IDS:
        probe = module_runtime.runtime_probe_config(module_id)
        assert probe is not None, f"Missing probe config for {module_id}"
        assert probe.get("kind") == "local_http_health", f"{module_id} probe kind is not local_http_health"


# ---------------------------------------------------------------------------
# probe_service_web_health dispatcher
# ---------------------------------------------------------------------------


def test_service_web_health_dispatcher_rejects_unknown_id() -> None:
    """probe_service_web_health must return blocked for an unknown module_id."""
    result = probe_service_web_health("not_a_real_service")
    assert result["status"] == "blocked"
    assert result["executed"] is False
    assert "not_a_real_service" in result["reason"]


def test_service_web_health_dispatcher_rejects_moonraker() -> None:
    """moonraker uses moonraker_fleet kind, not service_web_health — must be blocked by dispatcher."""
    result = probe_service_web_health("moonraker")
    assert result["status"] == "blocked"
    assert result["executed"] is False


@pytest.mark.parametrize("module_id", _SERVICE_IDS)
def test_service_web_health_dispatcher_routes_to_correct_probe(
    module_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """probe_service_web_health must route each service ID to its named probe fn."""
    called = []

    def _fake_probe() -> dict[str, Any]:
        called.append(module_id)
        return {"status": "ready", "kind": "local_http_health", "module_id": module_id}

    monkeypatch.setattr(module_runtime, f"probe_{module_id}", _fake_probe)
    result = probe_service_web_health(module_id)
    assert called == [module_id], f"Expected probe_{module_id} to be called"
    assert result["module_id"] == module_id


# ---------------------------------------------------------------------------
# Blocked: no configured URL (env var absent)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id,probe_fn", list(_PROBE_FNS.items()))
def test_service_probe_blocked_when_no_env_url(
    module_id: str, probe_fn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each service probe must return setup_required when the env var is absent."""
    probe = module_runtime.runtime_probe_config(module_id)
    assert probe is not None
    args = [str(a) for a in (probe.get("args") or [])]
    env_name = args[0].strip() if args else ""

    # Remove the env var and the private env override so no URL is available.
    monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})

    result = probe_fn()
    assert result["status"] == "setup_required", (
        f"{module_id}: expected setup_required when {env_name} is unset, got {result['status']!r}"
    )
    assert result["executed"] is False
    assert result["return_code"] is None


# ---------------------------------------------------------------------------
# Blocked: non-local URL guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id,probe_fn", list(_PROBE_FNS.items()))
def test_service_probe_blocked_for_non_local_url(
    module_id: str, probe_fn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each service probe must refuse to probe a public internet URL."""
    probe = module_runtime.runtime_probe_config(module_id)
    assert probe is not None
    args = [str(a) for a in (probe.get("args") or [])]
    env_name = args[0].strip() if args else ""

    monkeypatch.setenv(env_name, "http://example.com/api")
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})

    result = probe_fn()
    assert result["status"] == "setup_required"
    assert result["executed"] is False
    assert "local" in result["reason"].lower() or "private" in result["reason"].lower()


# ---------------------------------------------------------------------------
# Happy path: HTTP 200 with matching token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id,probe_fn", list(_PROBE_FNS.items()))
def test_service_probe_ready_on_200_with_matching_token(
    module_id: str, probe_fn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the local service returns HTTP 200 with the expected body token, status must be ready."""
    probe = module_runtime.runtime_probe_config(module_id)
    assert probe is not None

    args = [str(a) for a in (probe.get("args") or [])]
    env_name = args[0].strip() if args else ""
    expected_token = args[2].strip().lower() if len(args) > 2 else ""
    default_url = str(probe.get("default_url") or "http://127.0.0.1:9999")

    monkeypatch.setenv(env_name, default_url)
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})

    # Build a body that contains the expected token.
    body_str = f'{{"status": "ok", "{expected_token}": "1.0"}}' if expected_token else '{"status": "ok"}'
    body_bytes = body_str.encode()

    mock_response = _mock_http_response(body_bytes, status=200)
    with patch("urllib.request.urlopen", return_value=mock_response):
        result = probe_fn()

    assert result["status"] == "ready", (
        f"{module_id}: expected ready on HTTP 200, got {result['status']!r}. reason={result.get('reason')}"
    )
    assert result["executed"] is True
    assert result["return_code"] == 0
    assert result["detected"] is True


# ---------------------------------------------------------------------------
# Unhappy path: connection error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id,probe_fn", list(_PROBE_FNS.items()))
def test_service_probe_setup_required_on_connection_error(
    module_id: str, probe_fn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the local service is unreachable, status must be setup_required (not an exception)."""
    probe = module_runtime.runtime_probe_config(module_id)
    assert probe is not None

    args = [str(a) for a in (probe.get("args") or [])]
    env_name = args[0].strip() if args else ""
    default_url = str(probe.get("default_url") or "http://127.0.0.1:9999")

    monkeypatch.setenv(env_name, default_url)
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})

    with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        result = probe_fn()

    assert result["status"] == "setup_required"
    assert result["executed"] is True
    assert result["return_code"] == 1
    assert result["detected"] is False


# ---------------------------------------------------------------------------
# Unhappy path: HTTP 4xx / token mismatch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id,probe_fn", list(_PROBE_FNS.items()))
def test_service_probe_setup_required_on_404(
    module_id: str, probe_fn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HTTP 404 from the local service must yield setup_required."""
    probe = module_runtime.runtime_probe_config(module_id)
    assert probe is not None

    args = [str(a) for a in (probe.get("args") or [])]
    env_name = args[0].strip() if args else ""
    default_url = str(probe.get("default_url") or "http://127.0.0.1:9999")

    monkeypatch.setenv(env_name, default_url)
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})

    mock_response = _mock_http_response(b'{"error": "not found"}', status=404)
    with patch("urllib.request.urlopen", return_value=mock_response):
        result = probe_fn()

    assert result["status"] == "setup_required"
    assert result["executed"] is True
    assert result["return_code"] == 1


# ---------------------------------------------------------------------------
# Runner contract: service_web_health_runner status
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id", _SERVICE_IDS)
def test_service_runner_contract_returns_service_web_health_runner_on_ready_probe(
    module_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """module_runner_contract must return runner_status=service_web_health_runner for a ready service probe."""

    def _ready_http_probe(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "ready",
            "kind": "local_http_health",
            "verifier": f"{module_id} health",
            "proof_gate_version": "local-http-health-verifier-v1",
            "path": f"HERMES3D_SOURCE_{module_id.upper()}_URL",
            "executed": True,
            "return_code": 0,
            "capabilities": ["read_only_http_probe"],
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _ready_http_probe)
    contract = module_runtime.module_runner_contract(
        {
            "id": module_id,
            "display_name": module_id.replace("_", " ").title(),
            "section": "services",
            "launch_kind": "service",
            "install_state": "installed",
            "local_path": "G:/Github/example",
        }
    )

    assert contract["runner_status"] == "service_web_health_runner", (
        f"{module_id}: expected service_web_health_runner, got {contract['runner_status']!r}"
    )
    assert contract["agent_executable"] is False
    assert contract["mutation_allowed"] is False
    assert contract["read_only_runner_available"] is True
    assert "verify" in contract["safe_actions"]


@pytest.mark.parametrize("module_id", _SERVICE_IDS)
def test_service_runner_contract_blocked_when_url_not_configured(
    module_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no URL is configured, the runner contract must be blocked."""

    def _setup_required_probe(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "setup_required",
            "kind": "local_http_health",
            "verifier": f"{module_id} health",
            "proof_gate_version": "local-http-health-verifier-v1",
            "path": f"HERMES3D_SOURCE_{module_id.upper()}_URL",
            "executed": False,
            "return_code": None,
            "capabilities": [],
            "reason": f"HERMES3D_SOURCE_{module_id.upper()}_URL is not configured; no local health proof was attempted.",
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _setup_required_probe)
    contract = module_runtime.module_runner_contract(
        {
            "id": module_id,
            "display_name": module_id.replace("_", " ").title(),
            "section": "services",
            "launch_kind": "service",
            "install_state": "installed",
            "local_path": "",
        }
    )

    assert contract["runner_status"] != "service_web_health_runner"
    assert contract["agent_executable"] is False
    assert contract["blocked_reason"] is not None


# ---------------------------------------------------------------------------
# module_read_only_runner_contract: service rows get read_only_api_runner_ready
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id", _SERVICE_IDS)
def test_service_read_only_runner_contract_accepted_on_ready_probe(
    module_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """module_read_only_runner_contract must report accepted=True for a ready service probe."""

    def _ready_http_probe(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "ready",
            "kind": "local_http_health",
            "verifier": f"{module_id} health",
            "proof_gate_version": "local-http-health-verifier-v1",
            "path": f"HERMES3D_SOURCE_{module_id.upper()}_URL",
            "executed": True,
            "return_code": 0,
            "capabilities": ["read_only_http_probe"],
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _ready_http_probe)
    contract = module_runtime.module_read_only_runner_contract(
        {
            "id": module_id,
            "display_name": module_id.replace("_", " ").title(),
            "section": "services",
            "launch_kind": "service",
            "install_state": "installed",
        }
    )

    assert contract["accepted"] is True
    assert contract["read_only_runner_available"] is True
    assert contract["agent_executable"] is False
    assert contract["mutation_allowed"] is False
    assert contract["process_start_allowed"] is False
    assert contract["runner_status"] == "read_only_api_runner_ready"


# ---------------------------------------------------------------------------
# Probe is truly read-only: no POST, no mutation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id,probe_fn", list(_PROBE_FNS.items()))
def test_service_probe_uses_only_get_method(
    module_id: str, probe_fn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The probe must only use HTTP GET (never POST, PUT, DELETE, PATCH)."""
    probe = module_runtime.runtime_probe_config(module_id)
    assert probe is not None

    args = [str(a) for a in (probe.get("args") or [])]
    env_name = args[0].strip() if args else ""
    default_url = str(probe.get("default_url") or "http://127.0.0.1:9999")

    monkeypatch.setenv(env_name, default_url)
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})

    captured_requests: list[urllib.request.Request] = []

    def _capture_urlopen(request: urllib.request.Request, timeout: float) -> Any:
        captured_requests.append(request)
        raise OSError("intercepted")

    with patch("urllib.request.urlopen", side_effect=_capture_urlopen):
        probe_fn()

    assert len(captured_requests) == 1, f"{module_id}: expected exactly 1 HTTP request"
    req = captured_requests[0]
    method = req.get_method().upper()
    assert method == "GET", f"{module_id}: expected GET, got {method!r}"
