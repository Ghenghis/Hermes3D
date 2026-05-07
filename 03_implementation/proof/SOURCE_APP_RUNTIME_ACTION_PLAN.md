# Source OS Runtime Action Plan

Generated: 2026-05-07T11:28:22.689690+00:00

This plan is generated from the Source OS proof JSONs. It is the durable queue for the remaining 60-app runtime work: no app row is considered Hermes Agent usable unless a bounded verifier proves it and the UI shows that proof.

## Current Truth

- Source-backed apps: 60
- Runtime-ready apps: 31
- Runner-not-registered rows: 22
- Runtime-repair-required rows: 5
- Source-install-available rows: 0
- Open P0 runner/repair rows: 29
- Verified Hermes Agent CLIs: 7
- Agent-executable runner contracts: 7
- CLI/service signals needing verifiers: 33
- Blocked rows: 2

## Correction Rules

- A source checkout is not a working app by itself.
- A README command, package script, or desktop launcher is only a signal until a local non-destructive verifier passes.
- Hermes Agents may execute only verifier-backed runners, never raw unreviewed shell commands from docs.
- Setup/update/install stays plan-only until backup, smoke gate, proof event, and rollback policy exist.
- S1 remains camera/read-only and action-locked until the user changes printer policy.

## Verified Agent CLI Rows

| App | Section | Verifier | Proof gate | Next safe work |
| --- | --- | --- | --- | --- |
| Hermes Agent (NousResearch) | agents | Hermes Agent source CLI | python-module-cli-verifier-v1 | Expose bounded Hermes Agent runner using Hermes Agent source CLI; add dry-run smoke before mutating outputs. |
| Blender | modelers | Blender CLI | agent-cli-verifier-v1 | Expose bounded Hermes Agent runner using Blender CLI; add dry-run smoke before mutating outputs. |
| OpenSCAD | modelers | OpenSCAD CLI | runtime-verifier-v1 | Expose bounded Hermes Agent runner using OpenSCAD CLI; add dry-run smoke before mutating outputs. |
| CuraEngine | slicers | CuraEngine CLI | agent-cli-verifier-v1 | Expose bounded Hermes Agent runner using CuraEngine CLI; add dry-run smoke before mutating outputs. |
| FLSUN Slicer | slicers | FLSUN Slicer CLI | runtime-verifier-v1 | Expose bounded Hermes Agent runner using FLSUN Slicer CLI; add dry-run smoke before mutating outputs. |
| OrcaSlicer | slicers | OrcaSlicer CLI | runtime-verifier-v1 | Expose bounded Hermes Agent runner using OrcaSlicer CLI; add dry-run smoke before mutating outputs. |
| PrusaSlicer | slicers | PrusaSlicer CLI | runtime-verifier-v1 | Expose bounded Hermes Agent runner using PrusaSlicer CLI; add dry-run smoke before mutating outputs. |

## P0 Runner Gaps

These rows are installed/source-ready but not Hermes Agent runnable yet. They must remain disabled or plan-only until the acceptance gate passes.

Open P0 rows: 29

### Cli Preferred Gap (3)

| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |
| --- | --- | --- | --- | --- | --- |
| Slic3r | slicers | desktop_or_cli | documentation_cli_signal_needs_verifier | cli_version_help_or_dry_run | Register cli_version_help_or_dry_run; then `/api/modules/slic3r/runtime/verify` must return ready with proof before any agent execution. |
| Strec3D | slicers | cli_worker | documentation_cli_signal_needs_verifier | cli_version_help_or_dry_run | Register cli_version_help_or_dry_run; then `/api/modules/strec3d/runtime/verify` must return ready with proof before any agent execution. |
| SuperSlicer | slicers | desktop_or_cli | documentation_cli_signal_needs_verifier | cli_version_help_or_dry_run | Register cli_version_help_or_dry_run; then `/api/modules/superslicer/runtime/verify` must return ready with proof before any agent execution. |

### Desktop App Gap (3)

| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |
| --- | --- | --- | --- | --- | --- |
| FreeCAD | modelers | desktop_app | documentation_cli_signal_needs_verifier | Find a safe CLI/headless mode or add an explicit desktop bridge smoke. | Register module_specific_safe_verifier; then `/api/modules/freecad/runtime/verify` must return ready with proof before any agent execution. |
| SolveSpace | modelers | desktop_app | documentation_cli_signal_needs_verifier | Find a safe CLI/headless mode or add an explicit desktop bridge smoke. | Register module_specific_safe_verifier; then `/api/modules/solvespace/runtime/verify` must return ready with proof before any agent execution. |
| MatterControl | slicers | desktop_app | documentation_cli_signal_needs_verifier | Find a safe CLI/headless mode or add an explicit desktop bridge smoke. | Register module_specific_safe_verifier; then `/api/modules/mattercontrol/runtime/verify` must return ready with proof before any agent execution. |

### Gpu Worker Gap (3)

| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |
| --- | --- | --- | --- | --- | --- |
| Microsoft TRELLIS.2 | three_d_generation | gpu_worker | documentation_cli_signal_needs_verifier | dependency_model_cache_gpu_probe | Register dependency_model_cache_gpu_probe; then `/api/modules/trellis/runtime/verify` must return ready with proof before any agent execution. |
| Tencent Hunyuan3D 2.1 | three_d_generation | gpu_worker | documentation_cli_signal_needs_verifier | dependency_model_cache_gpu_probe | Register dependency_model_cache_gpu_probe; then `/api/modules/hunyuan3d_2_1/runtime/verify` must return ready with proof before any agent execution. |
| TripoSR | three_d_generation | gpu_worker | documentation_cli_signal_needs_verifier | dependency_model_cache_gpu_probe | Register dependency_model_cache_gpu_probe; then `/api/modules/triposr/runtime/verify` must return ready with proof before any agent execution. |

### Npm Package Gap (1)

| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |
| --- | --- | --- | --- | --- | --- |
| Azure Speech SDK JS | agents | npm_package | documentation_cli_signal_needs_verifier | node_package_metadata_or_script_help | Register node_package_metadata_or_script_help; then `/api/modules/azure_speech_sdk_js/runtime/verify` must return ready with proof before any agent execution. |

### Python Worker Gap (5)

| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |
| --- | --- | --- | --- | --- | --- |
| CadQuery | modelers | python_worker | documentation_cli_signal_needs_verifier | python_import_or_module_cli | Register python_import_or_module_cli; then `/api/modules/cadquery/runtime/verify` must return ready with proof before any agent execution. |
| Open3D | modelers | python_worker | documentation_cli_signal_needs_verifier | python_import_or_module_cli | Register python_import_or_module_cli; then `/api/modules/open3d/runtime/verify` must return ready with proof before any agent execution. |
| build123d | modelers | python_worker | documentation_cli_signal_needs_verifier | python_import_or_module_cli | Register python_import_or_module_cli; then `/api/modules/build123d/runtime/verify` must return ready with proof before any agent execution. |
| numpy-stl | modelers | python_worker | cli_candidate_needs_verifier | python_import_or_module_cli | Register python_import_or_module_cli; then `/api/modules/numpy_stl/runtime/verify` must return ready with proof before any agent execution. |
| pymesh | modelers | python_worker | no_local_cli_signal | python_import_or_module_cli | Register python_import_or_module_cli; then `/api/modules/pymesh/runtime/verify` must return ready with proof before any agent execution. |

### Runner Gap (5)

| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |
| --- | --- | --- | --- | --- | --- |
| Marlin | firmware | firmware_source | no_local_cli_signal | Use source/reference proof only until a safe compile/version verifier is defined. | Register read_only_firmware_source_inventory; then `/api/modules/marlin/runtime/verify` must return ready with proof before any agent execution. |
| Prusa Firmware | firmware | firmware_source | no_local_cli_signal | Use source/reference proof only until a safe compile/version verifier is defined. | Register read_only_firmware_source_inventory; then `/api/modules/prusa_firmware/runtime/verify` must return ready with proof before any agent execution. |
| RepRapFirmware | firmware | firmware_source | no_local_cli_signal | Use source/reference proof only until a safe compile/version verifier is defined. | Register read_only_firmware_source_inventory; then `/api/modules/reprapfirmware/runtime/verify` must return ready with proof before any agent execution. |
| Repetier Firmware | firmware | firmware_source | no_local_cli_signal | Use source/reference proof only until a safe compile/version verifier is defined. | Register read_only_firmware_source_inventory; then `/api/modules/repetier_firmware/runtime/verify` must return ready with proof before any agent execution. |
| Smoothieware | firmware | firmware_source | no_local_cli_signal | Use source/reference proof only until a safe compile/version verifier is defined. | Register read_only_firmware_source_inventory; then `/api/modules/smoothieware/runtime/verify` must return ready with proof before any agent execution. |

### Service Gap (6)

| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |
| --- | --- | --- | --- | --- | --- |
| Manyfold | library | service | documentation_cli_signal_needs_verifier | local_health_endpoint_or_process_probe | Register local_health_endpoint_or_process_probe; then `/api/modules/manyfold/runtime/verify` must return ready with proof before any agent execution. |
| Open Filament Database | materials | service | cli_candidate_needs_verifier | local_health_endpoint_or_process_probe | Register local_health_endpoint_or_process_probe; then `/api/modules/open_filament_database/runtime/verify` must return ready with proof before any agent execution. |
| FDM Monster | print_farm | service | cli_candidate_needs_verifier | local_health_endpoint_or_process_probe | Register local_health_endpoint_or_process_probe; then `/api/modules/fdm_monster/runtime/verify` must return ready with proof before any agent execution. |
| OctoPrint | print_farm | service | cli_candidate_needs_verifier | local_health_endpoint_or_process_probe | Register local_health_endpoint_or_process_probe; then `/api/modules/octoprint/runtime/verify` must return ready with proof before any agent execution. |
| ComfyUI | three_d_generation | service | documentation_cli_signal_needs_verifier | local_health_endpoint_or_process_probe | Register local_health_endpoint_or_process_probe; then `/api/modules/comfyui/runtime/verify` must return ready with proof before any agent execution. |
| ComfyUI TRELLIS.2 Wrapper | three_d_generation | service | documentation_cli_signal_needs_verifier | local_health_endpoint_or_process_probe | Register local_health_endpoint_or_process_probe; then `/api/modules/comfyui_trellis_wrapper/runtime/verify` must return ready with proof before any agent execution. |

### Web App Gap (3)

| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |
| --- | --- | --- | --- | --- | --- |
| Fluidd | print_farm | web_app | service_or_setup_candidate_needs_verifier | local_http_health_or_route_smoke | Register local_http_health_or_route_smoke; then `/api/modules/fluidd/runtime/verify` must return ready with proof before any agent execution. |
| Mainsail | print_farm | web_app | service_or_setup_candidate_needs_verifier | local_http_health_or_route_smoke | Register local_http_health_or_route_smoke; then `/api/modules/mainsail/runtime/verify` must return ready with proof before any agent execution. |
| Kiri:Moto / GridSpace | slicers | web_app | service_or_setup_candidate_needs_verifier | local_http_health_or_route_smoke | Register local_http_health_or_route_smoke; then `/api/modules/kirimoto_gridspace/runtime/verify` must return ready with proof before any agent execution. |

## Runner Contract Status

/api/modules/runtime/runner-contracts is the canonical execution matrix for Hermes Agents. A row is executable only when its contract says `agent_executable=true`; all other rows stay Verify/Setup Plan only.

- agent_cli_ready: 7
- blocked: 2
- cli_runner_gap: 1
- desktop_app_runner_gap: 3
- gpu_worker_runner_gap: 3
- launcher_metadata_only: 3
- metadata_ready_needs_runner: 5
- npm_package_runner_gap: 1
- readonly_api_ready: 3
- runner_not_registered: 5
- runtime_repair_required: 5
- service_runner_gap: 6
- source_reference_only: 13
- web_app_runner_gap: 3

## P1 CLI/Service Signals Needing Verifiers

These include some rows that are already source/reference/package ready. They still are not agent-executable unless they also appear in the verified Agent CLI list above.

| App | Section | Signal type | Current proof tier | Next verifier |
| --- | --- | --- | --- | --- |
| Azure Speech SDK JS | agents | documentation_cli_signal_needs_verifier | npm_package_gap | Confirm the documented command in the local runtime and register a verifier. |
| Blender MCP Candidates | agents | cli_candidate_needs_verifier | package_or_import_ready | Add a non-destructive CLI verifier before exposing this to Hermes Agents. |
| Kiln | agents | documentation_cli_signal_needs_verifier | source_reference_ready | Confirm the documented command in the local runtime and register a verifier. |
| Manyfold | library | documentation_cli_signal_needs_verifier | service_gap | Confirm the documented command in the local runtime and register a verifier. |
| Open Filament Database | materials | cli_candidate_needs_verifier | service_gap | Add a non-destructive CLI verifier before exposing this to Hermes Agents. |
| CadQuery | modelers | documentation_cli_signal_needs_verifier | python_worker_gap | Confirm the documented command in the local runtime and register a verifier. |
| FreeCAD | modelers | documentation_cli_signal_needs_verifier | desktop_app_gap | Confirm the documented command in the local runtime and register a verifier. |
| Manifold | modelers | documentation_cli_signal_needs_verifier | package_or_import_ready | Confirm the documented command in the local runtime and register a verifier. |
| MeshLab | modelers | documentation_cli_signal_needs_verifier | package_or_import_ready | Confirm the documented command in the local runtime and register a verifier. |
| Open3D | modelers | documentation_cli_signal_needs_verifier | python_worker_gap | Confirm the documented command in the local runtime and register a verifier. |
| SolveSpace | modelers | documentation_cli_signal_needs_verifier | desktop_app_gap | Confirm the documented command in the local runtime and register a verifier. |
| build123d | modelers | documentation_cli_signal_needs_verifier | python_worker_gap | Confirm the documented command in the local runtime and register a verifier. |
| numpy-stl | modelers | cli_candidate_needs_verifier | python_worker_gap | Add a non-destructive CLI verifier before exposing this to Hermes Agents. |
| trimesh | modelers | cli_candidate_needs_verifier | package_or_import_ready | Add a non-destructive CLI verifier before exposing this to Hermes Agents. |
| truck | modelers | documentation_cli_signal_needs_verifier | source_reference_ready | Confirm the documented command in the local runtime and register a verifier. |
| FDM Monster | print_farm | cli_candidate_needs_verifier | service_gap | Add a non-destructive CLI verifier before exposing this to Hermes Agents. |
| Fluidd | print_farm | service_or_setup_candidate_needs_verifier | web_app_gap | Add a health/version/setup verifier before exposing service or setup actions. |
| Mainsail | print_farm | service_or_setup_candidate_needs_verifier | web_app_gap | Add a health/version/setup verifier before exposing service or setup actions. |
| Moonraker | print_farm | cli_candidate_needs_verifier | service_api_ready | Add a non-destructive CLI verifier before exposing this to Hermes Agents. |
| OctoFarm | print_farm | service_or_setup_candidate_needs_verifier | source_reference_ready | Add a health/version/setup verifier before exposing service or setup actions. |
| OctoPrint | print_farm | cli_candidate_needs_verifier | service_gap | Add a non-destructive CLI verifier before exposing this to Hermes Agents. |
| Kiri:Moto / GridSpace | slicers | service_or_setup_candidate_needs_verifier | web_app_gap | Add a health/version/setup verifier before exposing service or setup actions. |
| MatterControl | slicers | documentation_cli_signal_needs_verifier | desktop_app_gap | Confirm the documented command in the local runtime and register a verifier. |
| Slic3r | slicers | documentation_cli_signal_needs_verifier | cli_preferred_gap | Confirm the documented command in the local runtime and register a verifier. |
| Strec3D | slicers | documentation_cli_signal_needs_verifier | cli_preferred_gap | Confirm the documented command in the local runtime and register a verifier. |
| SuperSlicer | slicers | documentation_cli_signal_needs_verifier | cli_preferred_gap | Confirm the documented command in the local runtime and register a verifier. |
| ComfyUI | three_d_generation | documentation_cli_signal_needs_verifier | service_gap | Confirm the documented command in the local runtime and register a verifier. |
| ComfyUI Frontend | three_d_generation | service_or_setup_candidate_needs_verifier | source_reference_ready | Add a health/version/setup verifier before exposing service or setup actions. |
| ComfyUI TRELLIS.2 Wrapper | three_d_generation | documentation_cli_signal_needs_verifier | service_gap | Confirm the documented command in the local runtime and register a verifier. |
| Microsoft TRELLIS.2 | three_d_generation | documentation_cli_signal_needs_verifier | gpu_worker_gap | Confirm the documented command in the local runtime and register a verifier. |
| Tencent Hunyuan3D 2.1 | three_d_generation | documentation_cli_signal_needs_verifier | gpu_worker_gap | Confirm the documented command in the local runtime and register a verifier. |
| TripoSR | three_d_generation | documentation_cli_signal_needs_verifier | gpu_worker_gap | Confirm the documented command in the local runtime and register a verifier. |
| 3D Box Generator | utilities | service_or_setup_candidate_needs_verifier | source_reference_ready | Add a health/version/setup verifier before exposing service or setup actions. |

## Launcher Metadata Only

These can prove local desktop app presence, but they are not Hermes Agent CLI runners yet.

| App | Section | Launcher | Required correction |
| --- | --- | --- | --- |
| Printrun | print_farm | G:/Github/apps/Pronterface.exe | Do not call this agent CLI-ready; add CLI/API smoke or explicit desktop bridge before agent execution. |
| BambuStudio | slicers | C:/Program Files/Bambu Studio/bambu-studio.exe | Do not call this agent CLI-ready; add CLI/API smoke or explicit desktop bridge before agent execution. |
| Ultimaker Cura | slicers | C:/Program Files/UltiMaker Cura 5.12.1/UltiMaker-Cura.exe | Do not call this agent CLI-ready; add CLI/API smoke or explicit desktop bridge before agent execution. |

## Rollup

### Runner Gap Tiers

- cli_preferred_gap: 3
- desktop_app_gap: 3
- gpu_worker_gap: 3
- npm_package_gap: 1
- python_worker_gap: 5
- runner_gap: 5
- service_gap: 6
- web_app_gap: 3

### CLI Surface Candidate Tiers

- cli_candidate_needs_verifier: 7
- documentation_cli_signal_needs_verifier: 20
- service_or_setup_candidate_needs_verifier: 6

## Verification Commands

Run these after any Source OS runtime, verifier, or UI wording change:

```powershell
python 03_implementation\scripts\audit_source_registry_truth.py
python 03_implementation\scripts\audit_source_cli_agent_readiness.py
python 03_implementation\scripts\audit_source_cli_surface.py
python 03_implementation\scripts\audit_source_app_completion.py
python 03_implementation\scripts\write_source_runtime_action_plan.py
python 03_implementation\scripts\scan_active_ui_no_fake.py
cd 03_implementation\ui; npm run lint; npx.cmd playwright test --config=playwright.e2e.config.ts --grep "Source OS|Plugins|Roadmap|Settings Environment"
```
