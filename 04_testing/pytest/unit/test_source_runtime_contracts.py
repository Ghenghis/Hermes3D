"""Source OS runner-contract policy tests."""

from __future__ import annotations

import pytest
from hermes3d.api.routes import modules
from hermes3d.services import module_runtime, source_service_supervisor


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
            {
                "id": "ready_cli",
                "display_name": "Ready CLI",
                "section": "utilities",
                "launch_kind": "cli_worker",
            },
            {
                "id": "gap_cli",
                "display_name": "Gap CLI",
                "section": "slicers",
                "launch_kind": "cli_worker",
            },
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
    assert contract["read_only_runner_available"] is True
    assert contract["runner_status"] == "metadata_ready_needs_runner"
    assert contract["required_verifier_family"] == "dry_run_worker_smoke"
    assert contract["mutation_allowed"] is False
    assert contract["safe_actions"] == [
        "verify",
        "setup_plan",
        "read_metadata",
        "read_only_runner_smoke",
    ]
    assert contract["blocked_reason"] is None

    read_only = module_runtime.module_read_only_runner_contract(
        {
            "id": "meshlab",
            "display_name": "MeshLab",
            "section": "modelers",
            "launch_kind": "desktop_or_cli",
            "install_state": "installed",
            "local_path": "G:/Github/example/MeshLab",
        }
    )
    assert read_only["accepted"] is True
    assert read_only["agent_executable"] is False
    assert read_only["runner_status"] == "read_only_metadata_runner_ready"
    assert read_only["mutation_allowed"] is False
    assert read_only["process_start_allowed"] is False


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
            "setup_steps": [
                "Install or select a Hermes3D Python runtime that can import cadquery."
            ],
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


@pytest.mark.parametrize(
    ("module_id", "display_name", "required_files"),
    [
        ("marlin", "Marlin", ["README.md", "docs"]),
        ("prusa_firmware", "Prusa Firmware", ["README.md", "CMakeLists.txt", "Firmware"]),
        ("reprapfirmware", "RepRapFirmware", ["README.md", "src"]),
        ("repetier_firmware", "Repetier Firmware", ["README.md", "src"]),
        ("smoothieware", "Smoothieware", ["COPYING", "src"]),
    ],
)
def test_firmware_source_inventory_is_reference_only_not_executable(
    monkeypatch,
    tmp_path,
    module_id: str,
    display_name: str,
    required_files: list[str],
) -> None:
    """Firmware rows may prove source inventory, but never become agent-executable.

    This is intentionally not a compile, flash, upload, or printer test.
    """

    monkeypatch.setattr(module_runtime, "_runtime_verifier_index", lambda: (False, {}))
    for relative in required_files:
        target = tmp_path / relative
        if "." in target.name:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("firmware source inventory proof\n", encoding="utf-8")
        else:
            target.mkdir(parents=True, exist_ok=True)

    runtime = module_runtime.module_runtime_probe(
        {
            "id": module_id,
            "display_name": display_name,
            "section": "firmware",
            "launch_kind": "firmware_source",
            "install_state": "installed",
            "local_path": str(tmp_path),
        }
    )
    contract = module_runtime.module_runner_contract(
        {
            "id": module_id,
            "display_name": display_name,
            "section": "firmware",
            "launch_kind": "firmware_source",
            "install_state": "installed",
            "local_path": str(tmp_path),
        }
    )

    assert runtime["status"] == "ready"
    assert runtime["kind"] == "source_inventory"
    assert runtime["executed"] is False
    assert runtime["proof_gate_version"] == "firmware-source-inventory-v1"
    assert contract["agent_executable"] is False
    assert contract["runner_status"] == "source_reference_only"
    assert contract["mutation_allowed"] is False
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
    assert contract["read_only_runner_available"] is True
    assert contract["runner_status"] == "readonly_api_ready"
    assert contract["required_verifier_family"] == "read_only_api_runner_contract"
    assert contract["safe_actions"] == [
        "verify",
        "setup_plan",
        "read_metadata",
        "read_only_runner_smoke",
    ]

    read_only = module_runtime.module_read_only_runner_contract(
        {
            "id": "fluidd",
            "display_name": "Fluidd",
            "section": "print_farm",
            "launch_kind": "web_app",
            "install_state": "installed",
            "local_path": "G:/Github/example/Fluidd",
        }
    )
    assert read_only["accepted"] is True
    assert read_only["runner_status"] == "read_only_api_runner_ready"
    assert read_only["printer_action_allowed"] is False


def test_read_only_runner_blocks_desktop_launcher(monkeypatch) -> None:
    def _ready_launcher(_mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "ready",
            "kind": "desktop_app",
            "verifier": "Bambu Studio launcher",
            "proof_gate_version": "desktop-launcher-metadata-v1",
            "path": "C:/Program Files/Bambu Studio/bambu-studio.exe",
            "executed": False,
            "return_code": None,
            "capabilities": ["desktop_slicer_launcher"],
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _ready_launcher)
    contract = module_runtime.module_read_only_runner_contract(
        {
            "id": "bambustudio",
            "display_name": "Bambu Studio",
            "section": "slicers",
            "launch_kind": "desktop_or_cli",
            "install_state": "installed",
            "local_path": "G:/Github/example/BambuStudio",
        }
    )

    assert contract["accepted"] is False
    assert contract["read_only_runner_available"] is False
    assert contract["mutation_allowed"] is False
    assert "package/import/local API" in contract["blocked_reason"]


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


@pytest.mark.parametrize(
    ("module_id", "display_name", "section", "launch_kind", "env_name"),
    [
        ("fdm_monster", "FDM Monster", "print_farm", "service", "HERMES3D_SOURCE_FDM_MONSTER_URL"),
        ("fluidd", "Fluidd", "print_farm", "web_app", "HERMES3D_SOURCE_FLUIDD_URL"),
        ("mainsail", "Mainsail", "print_farm", "web_app", "HERMES3D_SOURCE_MAINSAIL_URL"),
        ("octofarm", "OctoFarm", "print_farm", "service", "HERMES3D_SOURCE_OCTOFARM_URL"),
        ("octoprint", "OctoPrint", "print_farm", "service", "HERMES3D_SOURCE_OCTOPRINT_URL"),
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
def test_service_start_runner_contracts_are_safe_supervised_starts(
    monkeypatch,
    tmp_path,
    module_id: str,
    display_name: str,
    section: str,
    launch_kind: str,
    env_name: str,
) -> None:
    probe = module_runtime.BUILTIN_RUNTIME_PROBES[module_id]
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})
    monkeypatch.setenv(env_name, str(probe["default_url"]))
    monkeypatch.setattr(
        module_runtime,
        "_local_service_port_state",
        lambda _url: {"status": "free", "host": "127.0.0.1", "port": 1234},
    )
    monkeypatch.setattr(
        module_runtime, "_service_start_command_available", lambda _cmd, _path: True
    )

    contract = module_runtime.module_service_start_runner_contract(
        {
            "id": module_id,
            "display_name": display_name,
            "section": section,
            "launch_kind": launch_kind,
            "install_state": "installed",
            "local_path": str(tmp_path),
        }
    )

    assert contract["mutation_allowed"] is False
    assert contract["agent_can_execute_start_now"] == (module_id != "comfyui_trellis_wrapper")
    assert contract["env_name"] == env_name
    assert contract["url_guard"] == "local_private_only"
    if module_id == "comfyui_trellis_wrapper":
        assert contract["status"] == "setup_required"
        assert "not a standalone service" in contract["blocked_reason"]
        assert contract["execution_mode"] == "supervised_local_process_blocked_by_preflight"
        assert "start_supervised_runner" not in contract["safe_actions"]
    else:
        assert contract["status"] == "ready_to_start"
        assert contract["execution_mode"] == "supervised_local_process_with_post_start_health_proof"
        assert contract["start_preflight_passed"] is True
        assert "start_supervised_runner" in contract["safe_actions"]


def test_service_start_runner_rejects_public_url(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(module_runtime, "_private_runtime_env", lambda: {})
    monkeypatch.setenv("HERMES3D_SOURCE_FLUIDD_URL", "https://example.com")

    contract = module_runtime.module_service_start_runner_contract(
        {
            "id": "fluidd",
            "display_name": "Fluidd",
            "section": "print_farm",
            "launch_kind": "web_app",
            "install_state": "installed",
            "local_path": str(tmp_path),
        }
    )

    assert contract["status"] == "setup_required"
    assert contract["start_preflight_passed"] is False
    assert "localhost, a private LAN address, or a .local host" in contract["blocked_reason"]


def test_service_start_runner_unsupported_for_cli_row() -> None:
    contract = module_runtime.module_service_start_runner_contract(
        {
            "id": "prusaslicer",
            "display_name": "PrusaSlicer",
            "section": "slicers",
            "launch_kind": "cli_worker",
            "install_state": "installed",
            "local_path": "G:/Github/example/PrusaSlicer",
        }
    )

    assert contract["status"] == "unsupported"
    assert contract["start_preflight_passed"] is False


def test_runner_contract_routes_are_registered() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(modules.router)
    paths = {route.path for route in app.routes}

    assert "/api/modules/runtime/runner-contracts" in paths
    assert "/api/modules/{module_id}/runtime/runner-contract" in paths
    assert "/api/modules/{module_id}/runtime/read-only-runner" in paths
    assert "/api/modules/{module_id}/runtime/start-runner" in paths
    assert "/api/modules/{module_id}/runtime/stop-runner" in paths


def test_source_service_supervisor_blocks_failed_preflight() -> None:
    result = source_service_supervisor.start_source_service_runner(
        {"id": "fluidd", "display_name": "Fluidd"},
        {
            "module_id": "fluidd",
            "status": "setup_required",
            "start_preflight_passed": False,
            "blocked_reason": "HERMES3D_SOURCE_FLUIDD_URL is not configured.",
        },
        actor="pytest",
    )

    assert result["accepted"] is False
    assert result["status"] == "blocked"
    assert result["execution_mode"] == "supervised_local_process_blocked_by_preflight"


def test_source_service_supervisor_starts_registered_command_and_proves_health(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeProcess:
        pid = 4242

        def poll(self) -> None:
            return None

    started: dict[str, object] = {}

    def fake_popen(command, **kwargs):  # noqa: ANN001
        started["command"] = command
        started["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(source_service_supervisor, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(source_service_supervisor, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(source_service_supervisor.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        source_service_supervisor,
        "module_runtime_probe",
        lambda _mod, *, live=False: {
            "status": "ready",
            "kind": "local_http_health",
            "executed": True,
            "proof_gate_version": "local-http-health-verifier-v1",
        },
    )

    local_script = tmp_path / "serve.cmd"
    local_script.write_text("@echo off\n", encoding="utf-8")
    contract = {
        "module_id": "fluidd",
        "status": "ready_to_start",
        "start_preflight_passed": True,
        "local_path": str(tmp_path),
        "configured_url": "http://127.0.0.1:8083",
        "runner": {
            "command_preview": ["serve.cmd", "--host", "127.0.0.1"],
            "command_family": "test_service",
            "env": {"TEST_SERVICE_PORT": "8083"},
        },
    }

    result = source_service_supervisor.start_source_service_runner(
        {"id": "fluidd", "display_name": "Fluidd"},
        contract,
        actor="pytest",
        post_start_probe_attempts=1,
    )

    assert result["accepted"] is True
    assert result["status"] == "started_verified"
    assert result["runtime_ready"] is True
    assert result["process"]["pid"] == 4242
    assert started["command"][0] == str(local_script)
    kwargs = started["kwargs"]
    assert kwargs["shell"] is False
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["env"]["TEST_SERVICE_PORT"] == "8083"


def test_source_service_supervisor_sanitizes_secret_env(monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "secret")
    monkeypatch.setenv("PATH", "C:/Tools")

    env = source_service_supervisor._safe_process_env({"env": {"SERVICE_PORT": "1234"}})

    assert env["PATH"] == "C:/Tools"
    assert env["SERVICE_PORT"] == "1234"
    assert "MINIMAX_API_KEY" not in env
