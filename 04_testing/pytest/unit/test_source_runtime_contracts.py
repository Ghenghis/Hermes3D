"""Source OS runner-contract policy tests."""

from __future__ import annotations

from hermes3d.api.routes import modules
from hermes3d.services import module_runtime


def test_verified_cli_contract_is_agent_executable(monkeypatch) -> None:
    """Only a registered verifier that actually ran may become agent-executable."""

    def _ready_cli(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "ready",
            "kind": "cli",
            "verifier": "test --version",
            "proof_gate_version": "runtime-verifier-v1",
            "path": "C:/Tools/test.exe",
            "executed": True,
            "return_code": 0,
            "capabilities": ["version"],
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _ready_cli)
    contract = module_runtime.module_runner_contract(
        {
            "id": "example_cli",
            "display_name": "Example CLI",
            "section": "utilities",
            "launch_kind": "cli_worker",
            "install_state": "installed",
            "local_path": "G:/Github/example",
        }
    )

    assert contract["agent_executable"] is True
    assert contract["runner_status"] == "agent_cli_ready"
    assert contract["mutation_allowed"] is False
    assert contract["blocked_reason"] is None
    assert {"verify", "version_or_help", "dry_run_smoke_plan"} <= set(contract["safe_actions"])


def test_source_checkout_contract_remains_blocked_without_runner() -> None:
    contract = module_runtime.module_runner_contract(
        {
            "id": "source_only_cli",
            "display_name": "Source Only CLI",
            "section": "slicers",
            "launch_kind": "cli_worker",
            "install_state": "installed",
            "local_path": ".",
        }
    )

    assert contract["agent_executable"] is False
    assert contract["runtime_status"] == "source_ready"
    assert contract["runner_status"] == "cli_runner_gap"
    assert contract["required_verifier_family"] == "cli_version_help_or_dry_run"
    assert "must return ready with proof" in contract["acceptance_gate"]
    assert contract["safe_actions"] == ["verify", "setup_plan"]


def test_runner_contract_summary_counts_executable_and_gaps(monkeypatch) -> None:
    def _probe(mod: dict, *, live: bool = False) -> dict:
        if mod["id"] == "ready_cli":
            return {
                "status": "ready",
                "kind": "cli",
                "verifier": "ready --version",
                "proof_gate_version": "runtime-verifier-v1",
                "path": "C:/Tools/ready.exe",
                "executed": True,
                "return_code": 0,
                "capabilities": ["version"],
            }
        return {
            "status": "source_ready",
            "kind": "cli_worker",
            "verifier": "source checkout",
            "path": ".",
            "executed": False,
            "capabilities": [],
            "reason": "Source checkout is present; no safe module-specific runtime verifier is registered yet.",
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _probe)
    summary = module_runtime.module_runner_contracts(
        [
            {"id": "ready_cli", "display_name": "Ready CLI", "section": "utilities", "launch_kind": "cli_worker"},
            {"id": "gap_cli", "display_name": "Gap CLI", "section": "slicers", "launch_kind": "cli_worker"},
        ]
    )

    assert summary["count"] == 2
    assert summary["agent_executable"] == 1
    assert summary["runner_gaps"] == 1
    assert summary["by_runner_status"]["agent_cli_ready"] == 1
    assert summary["by_runner_status"]["cli_runner_gap"] == 1
    assert summary["by_gap_section"]["slicers"] == 1


def test_runner_contract_routes_are_registered() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(modules.router)
    paths = {route.path for route in app.routes}

    assert "/api/modules/runtime/runner-contracts" in paths
    assert "/api/modules/{module_id}/runtime/runner-contract" in paths
