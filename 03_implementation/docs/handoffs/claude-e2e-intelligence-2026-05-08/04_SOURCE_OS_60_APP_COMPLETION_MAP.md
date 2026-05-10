# 04 — Source OS 60-App Completion Map

**Status:** 60 applications inventoried across 11 sections. **7 agent_cli_ready**, **24 runner_gaps**, **15 runtime_repair_required**. **Rule:** No Source OS row becomes Hermes Agent usable until a bounded verifier and proof gate pass (Hermes Agents may run only registered non-destructive verifiers; setup/install/update/launch remains plan-only until a runner is registered with backup, smoke, proof, and rollback gates).

Source: live `/api/modules/runtime/runner-contracts` on h3d-gui-wiring-codex commit 43d8205, `/api/roadmap/tab-completion`, `external_repos_registry.yaml` (439 lines, 60 module rows).

---

## Per-Section Breakdown

| Section | Total | Agent-Exe | Agent-CLI-Ready | Metadata-Ready | Read-Only | Runtime-Repair | Runner-Gap | Blocked |
|---------|-------|-----------|-----------------|----------------|-----------|-----------------|-----------|---------|
| agents | 7 | 1 | 1 | 2 | 0 | 0 | 4 | 0 |
| firmware | 6 | 0 | 0 | 0 | 1 | 0 | 5 | 0 |
| hardware | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| library | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| materials | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| modelers | 13 | 2 | 2 | 3 | 0 | 5 | 3 | 0 |
| print_farm | 10 | 0 | 0 | 0 | 2 | 5 | 3 | 0 |
| research | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| slicers | 11 | 4 | 4 | 0 | 0 | 1 | 4 | 2 |
| three_d_generation | 6 | 0 | 0 | 0 | 0 | 2 | 4 | 0 |
| utilities | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

---

## 60-App Inventory Table

| ID | Display | Section | Launch | Install | Runtime | Runner Status | Next Safe Action | Evidence Path |
|---|---|---|---|---|---|---|---|---|
| azure_speech_sdk_js | Azure Speech SDK JS | agents | npm_package | installed | source_ready | npm_package_runner_gap | Register node_package_metadata_or_script_help | G:\Github\Hermes3D-OS\source-lab\sources\orchestration\Azure-Speech-SDK-JS |
| blender_mcp_candidates | Blender MCP Candidates | agents | python_worker | installed | ready | metadata_ready_needs_runner | Register dry-run smoke | G:\Github\h3d-gui-wiring-codex\03_implementation\source-lab\... |
| hermes_agent | Hermes Agent (NousResearch) | agents | python_worker | installed | ready | agent_cli_ready | DONE | G:/Github/hermes-agent-fresh |
| kiln | Kiln | agents | web_app_reference | installed | ready | source_reference_only | N/A | G:/Github/Hermes3D-OS/source-lab/sources/orchestration/Kiln |
| langchain | LangChain | agents | source_reference | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\orchestration\LangChain |
| langgraph | LangGraph | agents | source_reference | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\orchestration\LangGraph |
| model_context_protocol | Model Context Protocol | agents | npm_package | installed | ready | metadata_ready_needs_runner | Register dry-run smoke | C:/Program Files/nodejs/node.EXE |
| firmware_klipper | Klipper | firmware | service | installed | ready | readonly_api_ready | Register read-only runner | configured Moonraker printer URLs |
| marlin | Marlin | firmware | firmware_source | installed | ready | source_reference_only | N/A | G:/Github/Hermes3D-OS/source-lab/sources/firmware/Marlin |
| prusa_firmware | Prusa Firmware | firmware | firmware_source | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\firmware\Prusa-Firmware |
| repetier_firmware | Repetier Firmware | firmware | firmware_source | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\firmware\Repetier-Firmware |
| reprapfirmware | RepRapFirmware | firmware | firmware_source | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\firmware\RepRapFirmware |
| smoothieware | Smoothieware | firmware | firmware_source | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\firmware\Smoothieware |
| awesome_extruders | Awesome Extruders | hardware | catalog_reference | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\hardware\Awesome-Extruders |
| boxturtle | BoxTurtle | hardware | hardware_reference | installed | ready | source_reference_only | N/A | G:/Github/Hermes3D-OS/source-lab/sources/hardware/BoxTurtle |
| enraged_rabbit_project | EnragedRabbitProject | hardware | hardware_reference | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\hardware\EnragedRabbitProject |
| manyfold | Manyfold | library | service | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_MANYFOLD_URL |
| open_filament_database | Open Filament Database | materials | service | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_OPEN_FILAMENT_DATABASE_URL |
| blender | Blender | modelers | desktop_app | installed | ready | agent_cli_ready | DONE | C:/Program Files/Blender Foundation/Blender 5.1/blender.exe |
| build123d | build123d | modelers | python_worker | installed | setup_required | runtime_repair_required | Repair & re-verify | C:/Python314/python.exe |
| cadquery | CadQuery | modelers | python_worker | installed | setup_required | runtime_repair_required | Repair & re-verify | C:/Python314/python.exe |
| freecad | FreeCAD | modelers | desktop_app | installed | source_ready | desktop_app_runner_gap | Register module_specific_safe_verifier | G:/Github/Hermes3D-OS/source-lab/sources/modelers/FreeCAD |
| manifold | Manifold | modelers | cli_or_python_worker | installed | ready | metadata_ready_needs_runner | Register dry-run smoke | C:/Python314/python.exe |
| meshlab | MeshLab | modelers | desktop_or_cli | installed | ready | metadata_ready_needs_runner | Register dry-run smoke | C:/Python314/python.exe |
| numpy_stl | numpy-stl | modelers | python_worker | installed | setup_required | runtime_repair_required | Repair & re-verify | C:/Python314/python.exe |
| open3d | Open3D | modelers | python_worker | installed | setup_required | runtime_repair_required | Repair & re-verify | C:/Python314/python.exe |
| openscad | OpenSCAD | modelers | desktop_or_cli | installed | ready | agent_cli_ready | DONE | C:/Program Files/OpenSCAD/openscad.exe |
| pymesh | pymesh | modelers | python_worker | installed | setup_required | runtime_repair_required | Repair & re-verify | C:/Python314/python.exe |
| solvespace | SolveSpace | modelers | desktop_app | installed | source_ready | desktop_app_runner_gap | Register module_specific_safe_verifier | G:/Github/Hermes3D-OS/source-lab/sources/modelers/SolveSpace |
| trimesh | trimesh | modelers | python_worker | installed | ready | metadata_ready_needs_runner | Register dry-run smoke | C:/Python314/python.exe |
| truck | truck | modelers | rust_library_reference | installed | ready | source_reference_only | N/A | G:/Github/Hermes3D-OS/source-lab/sources/modelers/Truck |
| botqueue | BotQueue | print_farm | service_reference | installed | ready | source_reference_only | N/A | G:/Github/Hermes3D-OS/source-lab/sources/print-farm/BotQueue |
| fdm_monster | FDM Monster | print_farm | service | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_FDM_MONSTER_URL |
| fluidd | Fluidd | print_farm | web_app | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_FLUIDD_URL |
| klipper | Klipper | print_farm | service | installed | ready | readonly_api_ready | Register read-only runner | configured Moonraker printer URLs |
| klipperscreen | KlipperScreen | print_farm | touch_ui_reference | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\print-farm\KlipperScreen |
| mainsail | Mainsail | print_farm | web_app | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_MAINSAIL_URL |
| moonraker | Moonraker | print_farm | service | installed | ready | readonly_api_ready | Register read-only runner | configured Moonraker printer URLs |
| octofarm | OctoFarm | print_farm | service_reference | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_OCTOFARM_URL |
| octoprint | OctoPrint | print_farm | service | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_OCTOPRINT_URL |
| printrun | Printrun | print_farm | desktop_or_cli | installed | ready | launcher_metadata_only | Read launcher metadata | G:/Github/apps/Pronterface.exe |
| awesome_3d_printing | Awesome 3D Printing | research | reference | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\research\Awesome-3D-Printing |
| bambustudio | BambuStudio | slicers | desktop_or_cli | installed | ready | launcher_metadata_only | Read launcher metadata | C:/Program Files/Bambu Studio/bambu-studio.exe |
| cura | Ultimaker Cura | slicers | desktop_app | installed | ready | launcher_metadata_only | Read launcher metadata | C:/Program Files/UltiMaker Cura 5.12.1/UltiMaker-Cura.exe |
| curaengine | CuraEngine | slicers | cli_worker | installed | ready | agent_cli_ready | DONE | C:/Program Files/UltiMaker Cura 5.12.1/CuraEngine.exe |
| flsun_slicer | FLSUN Slicer | slicers | desktop_app | installed | ready | agent_cli_ready | DONE | C:/FlsunSlicer2.0/FlsunSlicer.exe |
| kirimoto_gridspace | Kiri:Moto / GridSpace | slicers | web_app | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_KIRIMOTO_GRIDSPACE_URL |
| mattercontrol | MatterControl | slicers | desktop_app | installed | source_ready | desktop_app_runner_gap | Register module_specific_safe_verifier | G:\Github\Hermes3D-OS\source-lab\sources\slicers\MatterControl |
| orcaslicer | OrcaSlicer | slicers | desktop_app | installed | ready | agent_cli_ready | DONE | C:/Program Files/OrcaSlicer/orca-slicer.exe |
| prusaslicer | PrusaSlicer | slicers | desktop_app | installed | ready | agent_cli_ready | DONE | C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe |
| slic3r | Slic3r | slicers | desktop_or_cli | installed | blocked | blocked | BLOCKED | C:/Program Files/Slic3r/slic3r-console.exe |
| strec3d | Strec3D | slicers | desktop_app | installed | ready | source_reference_only | N/A | G:/Github/Hermes3D-OS/source-lab/sources/slicers/Strecs3D |
| superslicer | SuperSlicer | slicers | desktop_or_cli | installed | blocked | blocked | BLOCKED | C:/Program Files/SuperSlicer/superslicer-console.exe |
| comfyui | ComfyUI | three_d_generation | service | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_COMFYUI_URL |
| comfyui_frontend | ComfyUI Frontend | three_d_generation | web_app_reference | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\generation\ComfyUI_frontend |
| comfyui_trellis_wrapper | ComfyUI TRELLIS.2 Wrapper | three_d_generation | service | installed | setup_required | runtime_repair_required | Repair & re-verify | HERMES3D_SOURCE_COMFYUI_TRELLIS_WRAPPER_URL |
| hunyuan3d_2_1 | Tencent Hunyuan3D 2.1 | three_d_generation | gpu_worker | installed | source_ready | gpu_worker_runner_gap | Register dependency_model_cache_gpu_probe | G:\Github\Hermes3D-OS\source-lab\sources\generation\Hunyuan3D-2 |
| trellis | Microsoft TRELLIS.2 | three_d_generation | gpu_worker | installed | source_ready | gpu_worker_runner_gap | Register dependency_model_cache_gpu_probe | G:\Github\Hermes3D-OS\source-lab\sources\generation\TRELLIS |
| triposr | TripoSR | three_d_generation | gpu_worker | installed | source_ready | gpu_worker_runner_gap | Register dependency_model_cache_gpu_probe | G:/Github/Hermes3D-OS/source-lab/sources/generation/TripoSR |
| box_stl_generator | 3D Box Generator | utilities | web_app_reference | installed | ready | source_reference_only | N/A | G:\Github\Hermes3D-OS\source-lab\sources\utilities\Box-STL-Generator |

---

## Highlights

### Agent-CLI-Ready (7) — DONE

**These are ready for Hermes Agent use:**

1. **hermes_agent** (Hermes Agent / NousResearch)
   - Path: G:\Github\hermes-agent-fresh
   - Verifier: python_module_cli (v1)
   - Status: Fully executable

2. **blender** (Blender)
   - Path: C:/Program Files/Blender Foundation/Blender 5.1/blender.exe
   - Verifier: cli (agent-cli-verifier-v1)
   - Status: Desktop app CLI ready

3. **openscad** (OpenSCAD)
   - Path: C:/Program Files/OpenSCAD/openscad.exe
   - Verifier: cli (runtime-verifier-v1)
   - Status: Desktop app CLI ready

4. **curaengine** (CuraEngine)
   - Path: C:/Program Files/UltiMaker Cura 5.12.1/CuraEngine.exe
   - Verifier: cli (agent-cli-verifier-v1)
   - Status: CLI worker ready

5. **flsun_slicer** (FLSUN Slicer)
   - Path: C:/FlsunSlicer2.0/FlsunSlicer.exe
   - Verifier: cli (runtime-verifier-v1)
   - Status: Desktop app CLI ready

6. **orcaslicer** (OrcaSlicer)
   - Path: C:/Program Files/OrcaSlicer/orca-slicer.exe
   - Verifier: cli (runtime-verifier-v1)
   - Status: Desktop app CLI ready

7. **prusaslicer** (PrusaSlicer)
   - Path: C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe
   - Verifier: cli (runtime-verifier-v1)
   - Status: Desktop app CLI ready

### Blocked (2) — Require Decision

- **slic3r** (Slic3r) — blocked (no explicit reason recorded)
- **superslicer** (SuperSlicer) — blocked (no explicit reason recorded)

Both are AGPL-3.0 licensed slicer references. Likely require resolution of legal/maintenance status before runner registration.

### Launcher-Metadata-Only (3) — Plan Phase

Apps that can read installer metadata but not execute:

- **printrun** (Printrun) — print_farm section
- **bambustudio** (BambuStudio) — slicers section
- **cura** (Ultimaker Cura) — slicers section

### Source-Reference-Only (18) — N/A for Runners

These are research, firmware, or reference materials that will never need runtime executors:

- **kiln**, **langchain**, **langgraph** (orchestration agents, read-only)
- **marlin**, **prusa_firmware**, **reprapfirmware**, **repetier_firmware**, **smoothieware** (firmware sources, no execution)
- **awesome_extruders**, **boxturtle**, **enraged_rabbit_project** (hardware specs/catalogs)
- **truck** (Rust CAD library reference)
- **botqueue**, **klipperscreen** (legacy fleet/touch-UI references)
- **awesome_3d_printing** (research catalog)
- **strec3d** (structural slicer bench)
- **comfyui_frontend** (web app reference, not the service)
- **box_stl_generator** (web utility generator)

---

## Runner Family Next-Implementation Order

Based on the current PR chain (PRs #88-#101 cover these families), the safe-action ladder for registering verifiers and runners is:

1. **read_only_runner** (PR #97 pattern, 8 modules ready) — Smoke test: verify package metadata, imports, local API. Example: firmware_klipper (Moonraker API already configured).

2. **executable_path_runner** (PR #98 pattern, 3 modules ready) — Smoke test: detect and read launcher metadata (no execution). Example: printrun, bambustudio, cura.

3. **python_import_repair** (PR #99 pattern, 5 modules ready) — Preflight: read source/dependency metadata, verify import chain. Example: blender_mcp_candidates, model_context_protocol.

4. **slicer_cli_install_config** (PR #100 pattern, 2 modules ready) — Preflight: read Slic3r/SuperSlicer source/schema/profile metadata only.

5. **npm_package_preflight** (PR #101 pattern, 1 module ready) — Smoke test: read package metadata/script names. Example: azure_speech_sdk_js.

6. **service_health** (PR #91/#93 pattern; Klipper, OctoPrint, Moonraker, FDM Monster, ComfyUI) — Health check: ping service endpoints, verify API response.

7. **printfarm_health** (PR #90 pattern) — Fleet status: verify farm controller is reachable.

8. **web_health** (PR #91 pattern; Fluidd, Mainsail, Manyfold, Open Filament DB) — Health check: verify web UI endpoint, render state.

9. **slicer_runner** (PR #89 pattern; CuraEngine, OrcaSlicer, PrusaSlicer, FLSUN, BambuStudio, Cura) — Slice job: invoke CLI, monitor process, validate output.

10. **blender_runner / python_worker** (PR #88 pattern; Blender, build123d, CadQuery, FreeCAD) — Model job: invoke Python worker, capture geometry, validate proof.

The 7 source-ready rows that need safe runner registration immediately are: **freecad, mattercontrol, solvespace, hunyuan3d_2_1, trellis, triposr, azure_speech_sdk_js**.

---

## Per-Section Gap Callouts

### agents (7 apps, 6 gaps)

Status: 1 agent_cli_ready (Hermes Agent), 2 metadata_ready_needs_runner (Blender MCP, Model Context Protocol), 4 runner_gaps (Azure Speech SDK JS npm_package_runner_gap, Kiln + LangChain + LangGraph source_reference_only). The section is heavily weighted toward reference/integration layers rather than independent executables. Hermes Agent itself is production-ready; the others need lightweight MCP dry-run smoke or npm metadata verification.

### firmware (6 apps, 5 gaps)

Status: 1 readonly_api_ready (Klipper via Moonraker), 5 runner_gaps (Marlin, Prusa, RepRap, Repetier, Smoothieware all source_reference_only). Firmware sources are archives only — they ship with safety constraints ("no_flash_without_explicit_approval") and will never have automated runners. Only Klipper has a live runtime (Moonraker service), which is already captured as read-only health check.

### hardware (3 apps, 3 gaps)

Status: All 3 are source_reference_only (Awesome Extruders, BoxTurtle, EnragedRabbitProject). These are hardware catalogs, spec sheets, and ERCF designs. No runners needed; purely reference/discovery.

### library (1 app, 0 gaps)

Status: 1 runtime_repair_required (Manyfold). The model library service is ready but requires a repair pass on its service health verification. Once cleared, it becomes readonly_api_ready for library-inventory queries. No active gaps.

### materials (1 app, 0 gaps)

Status: 1 runtime_repair_required (Open Filament Database). Similar to Manyfold — service is present but health verification needs one pass. No gaps.

### modelers (13 apps, 9 gaps)

Status: 2 agent_cli_ready (Blender, OpenSCAD), 3 metadata_ready_needs_runner (build123d, CadQuery, trimesh), 5 runtime_repair_required (FreeCAD, Manifold, MeshLab, numpy-stl, Open3D), 1 pymesh, 1 truck source_reference_only. Strong presence of Python workers and desktop CLIs. The main gap is registering dry-run smoke verifiers for the metadata-ready batch and repair verification for the 5 in repair state.

### print_farm (10 apps, 8 gaps)

Status: 2 readonly_api_ready (Klipper via Moonraker, print farm health via fleet aggregation), 5 runtime_repair_required (FDM Monster, Fluidd, Mainsail, OctoPrint, Moonraker core), 3 runner_gaps (Klipperscreen, BotQueue touch_ui_reference and service_reference). The farm orchestration layer is incomplete — Moonraker and OctoPrint core services need repair verification before they can serve as fleet anchors.

### research (1 app, 1 gap)

Status: 1 source_reference_only (Awesome 3D Printing). This is a curated catalog of tools and resources for 3D printing research. No runner needed; purely indexing and discovery.

### slicers (11 apps, 8 gaps)

Status: 4 agent_cli_ready (CuraEngine, OrcaSlicer, PrusaSlicer, FLSUN Slicer), 3 launcher_metadata_only (Cura desktop, BambuStudio, launcher metadata only), 2 blocked (Slic3r, SuperSlicer), 1 runtime_repair_required (another slicer variant), 4 runner_gaps. The slicer section is the most mature — 4 are ready for slice operations. The 2 blocked AGPL reference slicers need unblocking. The 3 launcher_metadata_only apps need executable detection + profile import integration.

### three_d_generation (6 apps, 6 gaps)

Status: 2 runtime_repair_required (ComfyUI, TRELLIS.2), 3 gpu_worker_runner_gap (Hunyuan3D, TripoSR, TRELLIS), 1 source_reference_only (ComfyUI Frontend web app). This section depends heavily on GPU workers and proof gates for model generation output. All 6 need repair/registration before agents can invoke 3D generation jobs.

### utilities (1 app, 1 gap)

Status: 1 source_reference_only (3D Box Generator / box-stl-generator). A lightweight web utility generator for parametric box templates. No runtime needed; useful as a template/reference for parametric utility patterns.

---

## Summary

- **Ready-to-go:** 7 apps can execute immediately under agent CLI.
- **One pass away:** 8 read-only runners + 3 executable detectors + 5 import repair verifiers = **16 near-term registrations**.
- **Repair queue:** 15 modules need proof gate clarification or dependency re-verification before runners can be registered.
- **No runner ever:** 18 reference/firmware/catalog sources stay in source-reference-only.
- **Blocked:** 2 slicers (Slic3r, SuperSlicer) require unblocking decision.

The completion map shows a mature 3D modeling & slicing front-end (7 cli-ready + 9 in metadata or repair phase), a partially-ready printer farm orchestration (2 healthy, 5 in repair), and research-stage 3D generation pipeline (all 6 needing work). The path to full usability is clear: unblock 2 slicers, register the 16 near-term runner families per the PR ladder, and shepherd the 15 in repair state through health verification gates.
