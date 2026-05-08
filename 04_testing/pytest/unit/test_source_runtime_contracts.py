"""Source OS runner-contract policy tests."""

from __future__ import annotations

import pytest
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


def test_python_import_contract_is_metadata_not_agent_executable(monkeypatch) -> None:
    """Import proof is useful runtime truth, but it is not a Hermes Agent runner."""

    def _ready_import(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "ready",
            "kind": "python_import",
            "verifier": "pymeshlab import",
            "proof_gate_version": "python-import-verifier-v1",
            "path": "python",
            "executed": True,
            "return_code": 0,
            "capabilities": ["mesh_load"],
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _ready_import)
    contract = module_runtime.module_runner_contract(
        {
            "id": "meshlab",
            "display_name": "MeshLab",
            "section": "modelers",
            "launch_kind": "desktop_or_cli",
            "install_state": "installed",
            "local_path": "G:/Github/example/MeshLab",
        }
    )

    assert contract["runtime_status"] == "ready"
    assert contract["agent_executable"] is False
    assert contract["runner_status"] == "metadata_ready_needs_runner"
    assert contract["required_verifier_family"] == "dry_run_worker_smoke"
    assert contract["mutation_allowed"] is False
    assert contract["safe_actions"] == ["verify", "setup_plan", "read_metadata"]


def test_setup_required_python_import_stays_in_repair_queue(monkeypatch) -> None:
    def _missing_import(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "setup_required",
            "kind": "python_import",
            "verifier": "cadquery import",
            "proof_gate_version": "python-import-verifier-v1",
            "path": "python",
            "executed": True,
            "return_code": 1,
            "capabilities": ["parametric_cad_worker"],
            "reason": "Python module cadquery is not importable in the Hermes3D backend runtime.",
            "setup_steps": ["Install or select a Hermes3D Python runtime that can import cadquery."],
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _missing_import)
    summary = module_runtime.module_runner_contracts(
        [
            {
                "id": "cadquery",
                "display_name": "CadQuery",
                "section": "modelers",
                "launch_kind": "python_worker",
                "install_state": "installed",
                "local_path": "G:/Github/example/CadQuery",
            }
        ]
    )
    contract = summary["contracts"][0]

    assert contract["agent_executable"] is False
    assert contract["runner_status"] == "runtime_repair_required"
    assert contract["blocked_reason"].startswith("Python module cadquery is not importable")
    assert contract["required_verifier_family"] == "python_import_or_module_cli"
    assert summary["runner_gaps"] == 1
    assert summary["by_runner_status"]["runtime_repair_required"] == 1


def test_source_inventory_contract_is_reference_only_not_executable(monkeypatch) -> None:
    def _ready_inventory(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "ready",
            "kind": "source_inventory",
            "verifier": "Strec3D source inventory",
            "proof_gate_version": "source-inventory-v1",
            "path": "G:/Github/Hermes3D-OS/source-lab/sources/slicers/Strecs3D",
            "executed": False,
            "return_code": 0,
            "capabilities": ["structural_infill_reference"],
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _ready_inventory)
    contract = module_runtime.module_runner_contract(
        {
            "id": "strec3d",
            "display_name": "Strec3D",
            "section": "slicers",
            "launch_kind": "desktop_app",
            "install_state": "installed",
            "local_path": "G:/Github/Hermes3D-OS/source-lab/sources/slicers/Strecs3D",
        }
    )

    assert contract["runtime_status"] == "ready"
    assert contract["agent_executable"] is False
    assert contract["runner_status"] == "source_reference_only"
    assert contract["required_verifier_family"] == "reference_parser_or_adapter_contract"
    assert contract["safe_actions"] == ["verify", "setup_plan", "read_metadata"]


def test_readonly_http_contract_is_not_agent_executable(monkeypatch) -> None:
    """A live health API proof is useful, but it is still read-only metadata."""

    def _ready_http(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "ready",
            "kind": "local_http_health",
            "verifier": "Fluidd local health",
            "proof_gate_version": "local-http-health-verifier-v1",
            "path": "HERMES3D_SOURCE_FLUIDD_URL",
            "detected": True,
            "executed": True,
            "return_code": 0,
            "capabilities": ["moonraker_web_ui_health", "read_only_http_probe"],
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _ready_http)
    contract = module_runtime.module_runner_contract(
        {
            "id": "fluidd",
            "display_name": "Fluidd",
            "section": "print_farm",
            "launch_kind": "web_app",
            "install_state": "installed",
            "local_path": "G:/Github/example/Fluidd",
        }
    )

    assert contract["runtime_status"] == "ready"
    assert contract["agent_executable"] is False
    assert contract["runner_status"] == "readonly_api_ready"
    assert contract["required_verifier_family"] == "read_only_api_runner_contract"
    assert contract["safe_actions"] == ["verify", "setup_plan", "read_metadata"]


def test_print_farm_health_probe_requires_configured_local_url(monkeypatch) -> None:
    monkeypatch.setattr(module_runtime, "_runtime_verifier_index", lambda: (False, {}))
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})
    monkeypatch.delenv("HERMES3D_SOURCE_FLUIDD_URL", raising=False)

    contract = module_runtime.module_runner_contract(
        {
            "id": "fluidd",
            "display_name": "Fluidd",
            "section": "print_farm",
            "launch_kind": "web_app",
            "install_state": "installed",
            "local_path": "G:/Github/example/Fluidd",
        }
    )

    assert contract["runtime_status"] == "setup_required"
    assert contract["verifier_kind"] == "local_http_health"
    assert contract["agent_executable"] is False
    assert contract["runner_status"] == "runtime_repair_required"
    assert contract["blocked_reason"].startswith("HERMES3D_SOURCE_FLUIDD_URL is not configured")


def test_print_farm_health_probe_rejects_public_urls(monkeypatch) -> None:
    monkeypatch.setattr(module_runtime, "_runtime_verifier_index", lambda: (False, {}))
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})
    monkeypatch.setenv("HERMES3D_SOURCE_FLUIDD_URL", "https://example.com")

    contract = module_runtime.module_runner_contract(
        {
            "id": "fluidd",
            "display_name": "Fluidd",
            "section": "print_farm",
            "launch_kind": "web_app",
            "install_state": "installed",
            "local_path": "G:/Github/example/Fluidd",
        }
    )

    assert contract["runtime_status"] == "setup_required"
    assert contract["runner_status"] == "runtime_repair_required"
    assert "localhost, a private LAN address, or a .local host" in contract["blocked_reason"]


@pytest.mark.parametrize(
    ("module_id", "display_name", "section", "launch_kind", "env_name"),
    [
        ("manyfold", "Manyfold", "library", "service", "HERMES3D_SOURCE_MANYFOLD_URL"),
        (
            "open_filament_database",
            "Open Filament Database",
            "materials",
            "service",
            "HERMES3D_SOURCE_OPEN_FILAMENT_DATABASE_URL",
        ),
        (
            "kirimoto_gridspace",
            "Kiri:Moto / GridSpace",
            "slicers",
            "web_app",
            "HERMES3D_SOURCE_KIRIMOTO_GRIDSPACE_URL",
        ),
        ("comfyui", "ComfyUI", "three_d_generation", "service", "HERMES3D_SOURCE_COMFYUI_URL"),
        (
            "comfyui_trellis_wrapper",
            "ComfyUI TRELLIS.2 Wrapper",
            "three_d_generation",
            "service",
            "HERMES3D_SOURCE_COMFYUI_TRELLIS_WRAPPER_URL",
        ),
    ],
)
def test_service_web_health_rows_require_configured_local_urls(
    monkeypatch,
    module_id: str,
    display_name: str,
    section: str,
    launch_kind: str,
    env_name: str,
) -> None:
    monkeypatch.setattr(module_runtime, "_runtime_verifier_index", lambda: (False, {}))
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})
    monkeypatch.delenv(env_name, raising=False)

    contract = module_runtime.module_runner_contract(
        {
            "id": module_id,
            "display_name": display_name,
            "section": section,
            "launch_kind": launch_kind,
            "install_state": "installed",
            "local_path": f"G:/Github/example/{module_id}",
        }
    )

    assert contract["runtime_status"] == "setup_required"
    assert contract["verifier_kind"] == "local_http_health"
    assert contract["agent_executable"] is False
    assert contract["runner_status"] == "runtime_repair_required"
    assert env_name in contract["blocked_reason"]


def test_local_http_health_probes_declare_default_urls_and_setup_steps() -> None:
    expected_envs = {
        "HERMES3D_SOURCE_FDM_MONSTER_URL",
        "HERMES3D_SOURCE_FLUIDD_URL",
        "HERMES3D_SOURCE_MAINSAIL_URL",
        "HERMES3D_SOURCE_OCTOFARM_URL",
        "HERMES3D_SOURCE_OCTOPRINT_URL",
        "HERMES3D_SOURCE_MANYFOLD_URL",
        "HERMES3D_SOURCE_OPEN_FILAMENT_DATABASE_URL",
        "HERMES3D_SOURCE_KIRIMOTO_GRIDSPACE_URL",
        "HERMES3D_SOURCE_COMFYUI_URL",
        "HERMES3D_SOURCE_COMFYUI_TRELLIS_WRAPPER_URL",
    }
    rows = [
        probe
        for probe in module_runtime.BUILTIN_RUNTIME_PROBES.values()
        if probe.get("kind") == "local_http_health"
    ]

    assert {str((probe.get("args") or [""])[0]) for probe in rows} == expected_envs
    assert len(rows) == 10
    for probe in rows:
        assert str(probe.get("default_url", "")).startswith("http://127.0.0.1:")
        assert probe.get("setup_steps")


def test_runner_contract_routes_are_registered() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(modules.router)
    paths = {route.path for route in app.routes}

    assert "/api/modules/runtime/runner-contracts" in paths
    assert "/api/modules/{module_id}/runtime/runner-contract" in paths
