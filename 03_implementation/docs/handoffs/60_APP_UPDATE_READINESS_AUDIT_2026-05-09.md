# Hermes3D Source OS — 60-App Update Readiness Audit (2026-05-09)

> **Status:** **Audit / planning lane only.** No app updates performed. No GUI changes. No source mutation outside this doc and Phase 4 patch proposals. The Hermes Agent v0.13.0 staged update was **formally deferred 2026-05-09** (see [HERMES_AGENT_V013_UPDATE_LANE_CPLUS_PY311_DOCKER_FORMAL_DEFER_2026-05-09.md](HERMES_AGENT_V013_UPDATE_LANE_CPLUS_PY311_DOCKER_FORMAL_DEFER_2026-05-09.md)); this audit's goal is to make every future update faster, safer, and not repeat that lane's pain.

> **Lane**: H3D-60APP-UPDATE-READINESS-AUDIT — MCP A2A `a2a_1778341133484_4efbb3dd`, owner `claude-lead-app-audit`, branch `claude/60app-update-audit` cut from `feat/hermes3d-7-complete-gui-repo-wiring`.

## 0. Goals (from user 2026-05-09)

The user wants apps to update **smoothly with rollback on issues**:
- revert to last version, or last working version
- auto-update toggle per app
- update-off per app
- update-include / exclude selection
- selectable target versions per app
- updates feel **instant** because: profiles precomputed, dep containers cached, quick smoke first, full proof async/background, rollback snapshot already exists, UI shows live status instead of blocking

This document is the precomputed-profile artifact that enables that UX.

## 1. Methodology

**Sources** (read-only; verified files cited per row):
- `hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml` (439 lines, 11 sections, 60 module rows)
- `03_implementation/proof/SOURCE_REGISTRY_TRUTH_AUDIT.json` (60 module rows)
- `03_implementation/src/hermes3d/db/load_modules.py` (`LAUNCH_KIND_OVERRIDES`, `SOURCE_OVERRIDES`)
- `03_implementation/proof/{SLICERS,MODELERS,GEN3D,PRINTFARM,FIRMWARE}_VERIFY_*.json`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/source-os-60-apps/REGISTRY.md`
- 6 Batch 1 research agents w/ web receipts (URLs in §6)

**Methodology**: 4-batch / 21-agent pipeline (Batch 1 = read-only research, Batch 2 = isolated proof lanes, Batch 3 = fix proposal review, Batch 4 = integration + decision). MCP-locked single doc, no concurrent file edits.

## 2. Total scope

**60 modules** across 11 sections:
- modelers 13, slicers 11, print_farm 10, agents 7, firmware 6, three_d_generation 6, hardware 3, library 1, materials 1, research 1, utilities 1
- (note: `klipper` is registered in BOTH `print_farm` AND `firmware` — separate rows; the loader renames the second to `firmware_klipper`)

## 3. Per-app profile matrix (60 rows)

The compact 9-column profile per app: **App | Update method | Proof command | Runtime env | Required deps | Rollback method | Known blockers | Recommended lane | Auto-update safe?**

For brevity, rows are grouped by section; full unabbreviated rows live in the per-section sub-files in `handoffs/60-apps/<section>.md` (to be split out in a follow-up commit). The matrix below is the canonical at-a-glance view.

### 3.1 Slicers (11)

| App | Update | Proof | Env | Deps | Rollback | Blockers | Lane | Auto-safe? |
|---|---|---|---|---|---|---|---|---|
| BambuStudio | `binary_release_download` (vendor installer) | filesystem-metadata only — no `--version` flag | win/linux/mac, OpenGL3 | VC++ runtime (Win), libwebkit (Linux) | `binary_replace_previous` | GUI-only, cloud-auth state, EULA | manual_user_confirm_per_release | **no** — vendor installer + cloud auth |
| Ultimaker Cura | `binary_release_download` | filesystem-metadata only (5.x has no CLI verb) | win/linux/mac, AppImage needs fuse2 | Qt6, Python 3.10/11 embedded, OpenGL4.1 | `binary_replace_previous` (parallel install) | per-version profile schema migrates; plug-in marketplace state | manual_user_confirm_per_release | **no** — profile schema risk |
| CuraEngine | bundled with Cura OR `git+cmake+protobuf` | `CuraEngine.exe` exit 0 with `Cura_SteamEngine version 5.12.1` | win/linux/wsl/docker (CLI) | C++17 + protobuf when self-built | `binary_replace_previous` | engine-version vs Cura JSON definition coupling | auto_safe_per_release (when bundled) | **conditional** — tied to Cura bundle |
| FLSUN Slicer | vendor zip from FLSUN wiki | `FlsunSlicer.exe --help` returns version banner | windows only (`os_support: [windows]`) | bundled wxWidgets | `manual_uninstall_then_reinstall` | proprietary license, vendor-only release cadence, profile-format coupling | manual_user_confirm_per_release | **no** — vendor-only |
| Kiri:Moto / GridSpace | `git+npm+setup-prod` | `curl /version` (currently `setup_required`, returns blocked) | Node 18+, browser WebGL2 | THREE.js | `git checkout previous tag + npm ci` | service worker cache pinning; verifier currently blocked | auto_safe_per_release once HTTP verifier passes | **conditional** |
| MatterControl | vendor MSI/PKG | `Get-Item .\MatterControl.exe).VersionInfo.FileVersion` | win .NET WPF, mac, linux .deb | .NET Framework 4.7.2+ (legacy) | `manual_uninstall_then_reinstall` | EULA pop-up, .NET Framework not on WSL/Docker, vendor cadence | manual_user_confirm_per_release | **no** |
| OrcaSlicer | `binary_release_download` | `orca-slicer.exe` exit 0 (empty stdout — return-code only) | win/linux AppImage/mac/wsl | OpenGL3.3, VC++ runtime, libwebkitgtk | `binary_replace_previous` | profile-format major-version bumps invalidate user printer-defs | auto_safe_per_release (patch) / manual (major) | **conditional** — yes for x.y.Z, no for x.Y.0 |
| PrusaSlicer | `binary_release_download` OR `git+build` | `prusa-slicer-console.exe --version` returns `PrusaSlicer-2.9.5-beta2` | win/linux AppImage/mac, headless wsl/docker | wxWidgets, OpenGL3.0, Boost | `binary_replace_previous` OR `git checkout vX.Y.Z` | beta-channel `2.9.5-beta2` installed; YAML pin `2.7.0/2.8.1` is older; AGPL-3.0 | auto_safe_per_release (stable) / manual (beta) | **conditional** — stable yes, beta no |
| Slic3r | `binary_release_download` (zip portable) | `slic3r-console.exe --version` (currently NOT installed; `cli_preferred_gap`) | win/linux/wsl/docker (Perl) | Perl 5.x + CPAN modules (Wx, OpenGL) | `binary_replace_previous` | repo abandoned (last meaningful release 2018) | pin_only_no_update | **no** — abandoned |
| Strec3D | `git_pull_then_build` (CMake, vendor verify needed) | source-only `git rev-parse` + `cmake --build` | win/linux/wsl/docker (preprocessor) | CMake 3.18+, C++17 | `git_checkout_previous_tag` | source provenance pending; alias `strec3d`→`strecs3d`; single researcher | pin_only_no_update | **no** — research-only |
| SuperSlicer | `binary_release_download` (slowed cadence) | `superslicer-console.exe --version` (currently NOT installed) | win/linux/wsl/docker | wxWidgets, Boost, OpenGL3 | `binary_replace_previous` | active fork lag vs PrusaSlicer; sole maintainer | manual_user_confirm_per_release | **no** — fork drift + stalled cadence |

**Slicer-class top risks (Batch 1 Agent 1 + 5):** profile-format invalidation; vendor-only / proprietary licenses; unverified CLI proof on Slic3r/SuperSlicer.

### 3.2 Modelers (13)

| App | Update | Proof | Env | Deps | Rollback | Blockers | Lane | Auto-safe? |
|---|---|---|---|---|---|---|---|---|
| Blender | `binary_release_download` + `git pull` for source mirror | `blender --version` | win/linux native, OpenGL4.3 | OpenGL4.3, MSVC redist, Python3.11 bundled | env-var pin `HERMES3D_BLENDER_PATH` to old exe | runtime is **5.1.1** but contract pins `4.2.0`; bpy API breaks 4.x→5.x | source-modelers (Blender lane) | **conditional** — version drift between contract & runtime |
| build123d | `pip install -U build123d` | `python -c "import build123d; print(build123d.__version__)"` | cross-platform (Python3.10–3.12) | OCP wheel ~150MB | `pip install build123d==<prev>` | OCP wheel not always present on Py3.13/3.14 (host runs 3.14) | source-modelers (python-worker tier) | **conditional** — Python<=3.12 only |
| CadQuery | `pip install -U cadquery` | `import cadquery; print(...)` | cross-platform (Python 3.10–3.12) | OCP / cadquery-ocp, ezdxf, multimethod, nlopt | `pip install cadquery==<prev>` | v1↔v2 API split; OCP wheel build fails on Py3.13+; conflicts with build123d | source-modelers | **no** — major-version split |
| FreeCAD | `binary_release_download` (AppImage / MSI); WB updates via Addon Manager | `freecad --version` | win/linux native, AppImage on Linux | Qt5/Qt6 (1.0.x is Qt6), Coin3D, OCC 7.7+ | side-by-side install dirs | 0.x→1.0 Qt6 break; OCC version coupling; not currently installed on host | source-modelers (desktop) | **no** — major workbench break |
| Manifold | `pip install -U manifold3d` (already pinned `>=2.5,<4.0`) | `import manifold3d; print(...)` | cross-platform | Eigen3, glm | `pip install manifold3d==<prev>` | trimesh 4.x calls into manifold3d for `.is_volume` — major bump can break trimesh | source-modelers | **conditional** — within `<4.0` cap |
| MeshLab | `binary_release_download` | `meshlabserver -h` (deprecated post-2022.02; use `pymeshlab`) | win/linux | Qt5, OpenGL3.3, VCG | keep prior installer dir | 2022.02 dropped CLI; `pymeshlab` is the programmable surface now | source-modelers (reference) | **no** — CLI deprecated |
| numpy-stl | `pip install -U numpy-stl` | `python -c "import stl; print(stl.__version__)"` | cross-platform | numpy>=1.20 | `pip install numpy-stl==<prev>` | confused with built-in `stl`; Py3.14 wheel may need rebuild | source-modelers | **yes** — small surface |
| Open3D | `pip install -U open3d` | `import open3d as o3d; print(o3d.__version__)` | cross-platform; CUDA needed for `open3d-cuda` | numpy, scipy, pillow; MKL on Win | `pip install open3d==<prev>` | no prebuilt wheel for Py3.13/3.14; CUDA driver coupling; ~600MB | source-modelers (gpu candidate) | **no** — Python+CUDA coupling |
| OpenSCAD | `binary_release_download` | `openscad --version` | win/linux | Qt5.15+, CGAL, MPFR, GMP, OpenCSG | keep prior installer | live host: 2021.01 (4yr stale); 2024+ snapshots add Manifold backend = different geom | source-modelers (primary) | **conditional** — engine swap |
| pymesh | override → `pymeshfix`; `pip install -U pymeshfix` | `import pymeshfix; print(...)` | cross-platform | numpy, pyvista (~80MB VTK 9.x) | `pip install pymeshfix==<prev>` | original `PyMesh/PyMesh` upstream unbuildable; relies on override | source-modelers (candidate) | **conditional** — safe only via override |
| SolveSpace | `binary_release_download` OR `git+build` | `solvespace --version` | win/linux | Qt-less custom UI; CMake, Eigen, mimalloc | keep prior installer | reference-only; thin CLI; 3.1+ file format change | source-modelers (reference) | **no** — reference-only |
| trimesh | `pip install -U trimesh` (pinned `>=4.0,<5.0`) | `import trimesh; print(trimesh.__version__)` | cross-platform | numpy + optional rtree/manifold3d/scipy/networkx/mapbox-earcut/shapely/embreex | `pip install trimesh==<prev>` | host: 4.12.1; trimesh 5.x will be breaking; missing plugins silently disable features | source-modelers (primary) | **yes** within `<5.0` cap |
| truck | `cargo install` OR `git+cargo build --release` | `cargo build -p truck-modeling` | cross-platform; Rust 1.75+ | Cargo / rustup | `git checkout <prev_tag> + cargo clean` | rust_library_reference; no FFI bindings shipped | source-modelers (research) | **no** — pure source ref |

**Modeler-class top risks:** Py 3.14 host has no prebuilt wheels for `open3d`/`cadquery-ocp`; contract drift Blender 4.2 vs runtime 5.1.1; trimesh plugin coupling silently disables truth_gate.

### 3.3 3D Generation (6)

| App | Update | Proof | Env | Deps | Rollback | Blockers | Lane | Auto-safe? |
|---|---|---|---|---|---|---|---|---|
| ComfyUI | `git pull + pip install -r requirements.txt` (code) + HF model download (weights) | `GET :8188/system_stats` + `git rev-parse HEAD` (current `fce0398470fe`) | Py3.10–3.12, NVIDIA GPU+CUDA recommended, VRAM 6GB-16GB+ | NVIDIA driver≥525, PyTorch+CUDA12, xformers, transformers, accelerate | `git checkout <prev_sha>` + venv re-pin | custom_nodes API churn; xformers/PyTorch ABI; Win triton wheels missing | Lane A (Service-class) | **code: yes** with venv freeze; custom_nodes: no |
| ComfyUI Frontend | `git_clone_pin_to_release` (read-only mirror) | `git rev-parse HEAD` (`1c541d8577a4`) | Node 18+/pnpm only if building | Node18, pnpm, Vite, TypeScript (build-time) | `git checkout <prev_sha>` | bundled in ComfyUI; standalone is dev reference | Lane R (Reference) | **yes** — read-only |
| ComfyUI TRELLIS.2 Wrapper | `git_clone_pin_to_release` + pip into ComfyUI venv | `git rev-parse HEAD` (`86d13d9eac4a`) + ComfyUI workflow JSON producing TRELLIS mesh | inherits ComfyUI host (Py3.10-3.12, CUDA12) | inherits ComfyUI venv + TRELLIS.2 model code/weights | `git checkout <prev_sha>` | **3rd-party** repo (`visualbruno/...`) — license `unknown` in truth-audit | Lane A (gated on license) | **no** — license unknown + 3rd-party |
| Tencent Hunyuan3D 2.1 | `git_clone_pin_to_release` (code) + HF model download (weights) | `git rev-parse` (`82920d643c0d`) + `pip show hy3dgen` | gpu_worker, CUDA mandatory, VRAM≥16GB (24GB safer) | NVIDIA≥535, torch+cu12, diffusers, transformers, xformers, trimesh, pymeshlab, optional Blender | `git checkout` + HF snapshot revision swap | **Tencent Hunyuan community license** — non-MIT/Apache; commercial-use thresholds apply; multi-GB weights | Lane G (GPU-worker) | **no** — non-permissive license + gpu_worker |
| Microsoft TRELLIS.2 | `git_clone_pin_to_release` + HF download | `git rev-parse` (`5565d240c4a4`) + `pip show trellis` | gpu_worker, CUDA mandatory, VRAM≥16GB | NVIDIA≥535, torch+cu12, xformers, kaolin, trimesh, **flash-attn (Linux/WSL2 only)**, custom CUDA extensions | `git checkout` + HF snapshot pin | CUDA-extension build at install; flash-attn Win-native unsupported; model weights license re-verify each release | Lane G (GPU-worker) | **no** — gpu_worker + CUDA-ext compile |
| TripoSR | `git_clone_pin_to_release` + HF download (small weights) | `git rev-parse` (`d26e33181947`) + `pip show triposr` | gpu_worker, fast-preview/low-VRAM (6-8GB), Win-native CUDA viable | NVIDIA≥525, torch+cu11/12, transformers, diffusers, trimesh, omegaconf, hf-hub, rembg, onnxruntime | `git checkout` + HF snapshot pin | low velocity = low risk; license `stabilityai/TripoSR` model card has historical research-only nuance | Lane G (low-risk subclass) | **marginal yes** for code; HITL for license re-verify |

**3D-gen top risks:** Hunyuan3D 2.1 license rider; gpu_worker CUDA toolchain mismatch; multi-GB weight delta.

### 3.4 Print-farm (10) + 3.5 Firmware (6)

**Safety asymmetry — services can be auto-updated with rollback; firmware CANNOT be auto-flashed.** All 6 firmware rows carry `safety: no_flash_without_explicit_approval` (`external_repos_registry.yaml:255, 262, 269, 276, 283, 290`). The `forbidden_flash_tokens` list (`FIRMWARE_VERIFY_2026-05-06.json:64-77`: `flash`, `upload`, `avrdude`, `pio run -t upload`, `make program`) MUST be enforced at the dispatcher layer.

| App | Class | Update | Proof | Env | Rollback | Blockers | Lane | Auto-safe? |
|---|---|---|---|---|---|---|---|---|
| FDM Monster | service | `docker compose pull` (preferred) or `git+npm+node build` | `GET :4000/api/settings` | docker or wsl+Node18 | pin Docker image tag | MongoDB schema migrations across major versions | auto_safe_per_release (Docker pin) | **conditional** — pinned tag + volume-mounted DB |
| Fluidd | web_app | static-asset replacement (`npm run build → dist/` to nginx) or release tarball | `GET /` 200/30x; `dist/version.txt` | linux klipper-host (Pi/SBC) | snapshot `dist/`, swap symlink | builds on Pi; nginx vhost binding | auto_safe_per_release | **yes** (static UI) |
| Klipper (service) | service | `kiauh` OR `git+pip+systemctl restart klipper` | `GET :7125/printer/info` | linux klipper-host | `git checkout <prev-tag>` + restart | print-in-progress; MCU firmware on board may need re-flash if wire-protocol bumps | manual_user_confirm_per_release | **no** — paired firmware flash may be needed |
| KlipperScreen | touch_ui_reference | `git+pip+systemctl restart KlipperScreen` | `systemctl is-active` + `git rev-parse` | linux klipper-host with HDMI/DSI touchscreen | `git checkout <prev>` + restart | reference-only without hardware; can't be runtime-verified on dev box | pin_only_no_update | **no** — UI for hardware not present |
| Mainsail | web_app | static-asset replacement | `GET /` 200; `dist/release_info.json` | linux klipper-host | snapshot `dist/`, swap symlink | same Pi/SBC remote-only | auto_safe_per_release | **yes** (static UI) |
| Moonraker | service | `kiauh` OR `git+pip+systemctl restart moonraker` | `GET :7125/server/info` (live: `v0.7.1-586-gbb526e0-dirty`) | linux klipper-host | `git checkout <prev-tag>` + restart | `[update_manager]` config drift; auth tokens in DB | auto_safe_per_release (with kiauh) | **conditional** — yes inside kiauh; no for raw pip |
| OctoFarm | service_reference | `git+npm+pm2 restart` (largely abandoned) | `GET :4000/api/system/info` if running | wsl/linux + Node | pin Docker image OR `git checkout <prev>` | **project effectively unmaintained**; superseded by FDM Monster | pin_only_no_update | **no** — abandoned |
| OctoPrint | service | `~/oprint/bin/pip install -U OctoPrint==<v> + systemctl restart`; plugins via plugin manager | `GET :5000/api/version` JSON | linux/win/wsl/docker | `pip install OctoPrint==<prev>`; plugin-by-plugin downgrade | plugin compat across major versions (1.10→1.11 breaks ~30%); DB migration | manual_user_confirm_per_release | **no** — plugin-compat probe needed |
| BotQueue | service_reference | **no update path** (verify_source_before_claiming) | `git rev-parse` against pinned SHA | wsl (PHP/MySQL legacy) | pin SHA only | source provenance not confirmed; abandoned | pin_only_no_update + verify_source | **no** |
| Printrun | desktop_or_cli | `git+pip` OR bundled `printrun-2.2.0_windows_x64_py3.10.zip` | `pronsole --help`; tested_version `2.2.0` | win bundled OR wsl | keep bundled zip + `pip install printrun==<prev>` | Py2/3 mixed legacy; wxPython on Win fragile; serial-port USB device claim | manual_user_confirm_per_release | **no** — desktop GUI + USB-serial |
| Klipper (firmware) | firmware (renamed `firmware_klipper`) | `vendor_signed_artifact_then_manual_flash`: build `klipper.bin` + `make flash` ONLY with explicit user approval | source-tree `git rev-parse` + Moonraker `/printer/info.software_version` | linux for compile; STM32/AVR/RP2040 MCU runtime | keep prior `out/klipper.bin` + `make flash KCONFIG_CONFIG=<prev>.config` | **double-registered** with service row; bumping host without re-flashing MCU breaks wire protocol | vendor_or_user_explicit_flash_only | **NO — never auto-flash** |
| Marlin | firmware_source | `compile_then_manual_flash_via_dfu`: `pio run -e <board>` (forbidden tokens include `pio run -t upload`) | `git rev-parse` (`03cc75f222c1`) + `Configuration.h` STRING_CONFIG_H_AUTHOR | wsl/linux for PlatformIO | keep prior `firmware.bin/.hex` + manual SD-card/DFU re-flash | per-board `Configuration.h` highly customised; upstream merges blow away local diffs | vendor_or_user_explicit_flash_only | **NO** |
| Prusa Firmware | firmware_source | `compile_then_manual_flash_via_dfu` (printer-side menu loads from USB stick) | `git rev-parse` (`f3e0dfd481a7`) + `Firmware/Configuration.h` FW_VERSION | linux (Prusa toolchain dockerfile) for compile | vendor-signed previous .hex + manual SD-card flash | MK2/MK3/MK4 different MCU families; bootloader re-flash needed on bricked board | vendor_or_user_explicit_flash_only | **NO** |
| Repetier Firmware | firmware_source | **no update path until repo confirmed** (verify_source_before_claiming) | `git rev-parse` against unverified `7cb3741323ba` | wsl for compile | vendor-signed previous .hex + manual flash | source provenance not confirmed; project niche | vendor_or_user_explicit_flash_only + verify_source | **NO** |
| RepRapFirmware | firmware_source | `vendor_signed_artifact_then_manual_flash`: download Duet3D `.bin`, copy to SD or upload via DWC | `git rev-parse` (`f4297adae651`) + Duet `M115` G-code | linux for compile; Duet board for flash | keep prior `.bin` + DWC "Upload Firmware" rollback | board-family fragmentation (Duet 2 / Duet 3 MB6HC / Mini5+); mismatched binary semi-bricks | vendor_or_user_explicit_flash_only | **NO** |
| Smoothieware | firmware_source | `compile_then_manual_flash_via_dfu`: `make` produces `firmware.bin` → SD card as `firmware.cur` | `git rev-parse` (`620e1622972b`) + `version` G-code | linux/wsl for compile | keep prior `firmware.bin` + SD-card swap | project effectively unmaintained; LPC1768/9 boards EOL | vendor_or_user_explicit_flash_only + pin_only_no_update | **NO** |

**Print-farm + firmware top risks:** auto-flash leakage (LLM-callable macros must be deny-listed); Klipper service/firmware decoupling (paired-update gate required); OctoPrint plugin breakage on auto-update.

### 3.6 Coding agents (3 + Hermes Agent in 60-app)

| App | Update | Proof | Env | Deps | Rollback | Blockers | Lane | Auto-safe? |
|---|---|---|---|---|---|---|---|---|
| Hermes Agent (NousResearch) | **staged endpoint** `POST /api/agents/update/staged` (`agent_updates.py:87-148`) — staged_backup_then_tag_checkout | `python -c "from hermes_cli import __version__; print(__version__)"` (returns `0.12.0`); `GET /api/agents/update/status` | Python>=3.11; Win 3.14 OK; Docker mirrors Py3.11-slim | `[all,dev]` extras (~30 pkg core; ~100MB+ full) | `_auto_repair_to_backup` (proven 4× in lanes A/B/Cplus); `POST /rollback`; backups are `git bundle --all` + dirty-zip in `var/hermes_agent_backups/<id>.bundle` | v0.13.0 **formally deferred 2026-05-09** (lane A: Win `pwd` import; lane B: 50 stale tests upstream removed in `66320de52` AFTER tag; Cplus Docker: 20 residuals — 10 systemd-DBus / 4 audio / 4 process / 2 transient) | staged_endpoint_lane_with_managed_patch | **conditional** — patch-tags within v2026.4.x: yes; v0.13.0+: NO until upstream tags v2026.5.8+ AND lands `is_container()/is_wsl()` skipif decorators (issue #22420) |
| OpenCode (sst/opencode) | `git pull && bun install && bun run build` (in `opencode-dev/packages/opencode`); user-side `HERMES3D_OPENCODE_BIN` env points at the static binary | `opencode --version` (returns `1.4.3-hermes3d`); wired through `/api/code-operator/cli-runners/preflight` | Bun-built static binary; cross-platform; build host needs Bun | build-time only (Bun, effect-language-service, drizzle-kit); runtime: none | pin `HERMES3D_OPENCODE_BIN` to known-good binary; rename prior build | Bun toolchain on Windows; no upstream "newer-version-available" probe wired today | manual_user_confirm_per_release until preflight adds upstream-version probe | **no** — preflight is detection-only |
| OpenHands (All-Hands-AI) | `pip install -U openhands-ai` OR `make build`; CLI at `~/.local/bin/openhands.exe` | `openhands --version` (returns `OpenHands CLI 1.16.0`); wired through `/cli-runners/preflight` | Python venv 3.12-3.13; Docker for sandbox `run` path | aiohttp, anthropic, anyio, browsergym-core, docker, fastmcp, litellm, mcp, openai==2.8 (PINNED), openhands-aci/sdk/agent-server/tools | `pip install openhands-ai==<prev>` | sandbox readiness gate (`code_sandbox_readiness().ready`); is_wsl=True in Docker Desktop containers causes systemd-D-Bus failures (same as Hermes Agent) | manual_user_confirm_per_release until automated pre-flight + sandbox readiness wired | **no** — gated by run path, fail-closed |

**Coding-agents top risks:** Hermes Agent v0.13.x silent acceptance (need `run_checks=true` guard); OpenCode binary-path drift; OpenHands transitive Python conflicts (`openai==2.8` vs `>=2.21,<3`).

### 3.7 MCP servers (5 entries — 3 in 60-app + 2 cross-cutting)

| App | Update | Proof | Env | Deps | Rollback | Blockers | Lane | Auto-safe? |
|---|---|---|---|---|---|---|---|---|
| hermes3d-locks (this repo, v0.7.0) | `git pull origin main && npm install` (Ghenghis/HermesProof) | `mcp__hermes3d-locks__hermes_doctor` returning `ok: true`; `npm test`; `npm run truth-gates` | Node>=20.0.0 (`package.json:65-67`); stdio JSON-RPC; win/linux/wsl | `@modelcontextprotocol/sdk@^1.29.0`, dotenv, zod | `git checkout <prior-tag>` + `npm ci`; `mcp-supervisor.mjs` keeps stdio alive across rollback | cascade-merge conflict on package.json + truth-gates.mjs (every squash-merge requires UNION resolution) | auto_safe_per_release_with_truth_gate_proof (standing merge auth covers green PRs) | **YES** — gated by `npm run truth-gates` |
| blender-mcp (ahujasid) | `uvx blender-mcp` (latest from PyPI) | `uvx blender-mcp --help` + `claude mcp list` | Blender>=4.2 running concurrently; uvx Py3.10+; localhost socket | uvx; Blender add-on `addon.py`; pillow; MCP SDK Python | `uvx blender-mcp==<v>`; clear `~/.cache/uv` | requires Blender process running on configured port; missing add-on = silent fail; tested_versions `0.1.0` only | manual_user_confirm_per_release (3rd-party, no truth-gate) | **no** |
| blender-mcp (VxAI) | manual provider install after validation | `claude mcp list` | same as ahujasid; experimental | VxAI fork; Blender; Python | re-run manual install of older revision | `version_policy: experimental`; `required: false`; backup provider only | manual_user_confirm_per_release | **no** |
| Model Context Protocol spec | `npm install @modelcontextprotocol/sdk` (we pin `^1.29.0`) | `npm ls @modelcontextprotocol/sdk` | reference repo; `launch_kind: npm_package` is misleading (it's a spec, not a daemon) | none at runtime; SDK is what matters and is in hermes3d-locks deps | pin SDK to prior minor in `package.json:61` and `npm ci` | spec changes propagate through SDK bumps | defer_to_sdk_update | **YES** — no executable artifact; SDK bumps follow hermes3d-locks lane |
| Claude Code bundled MCPs (class) — chrome-devtools, context7, playwright, serena, ccd_*, mcp-registry, Desktop_Commander, Windows-MCP, Figma, Claude_in_Chrome, Claude_Preview | handled by `claude` CLI itself | `claude mcp list`; system reminder enumerates connected servers | Claude Code host (≥current GA); per-MCP requirements | each MCP brings its own deps; opaque to Hermes3D | re-pin Claude Code version, or `claude plugin disable <name>` | "85 deferred tools" warning indicates surface-area pressure when many MCPs attach | defer_to_claude_code (out of Hermes3D scope, observe only) | **N/A for Hermes3D** |

**MCP-class top risks:** no central registry (Glob+Grep returned zero `mcp_server_registry.{json,yaml}`); cascade-merge conflicts; STRICT 2026-05-03 disconnect-resilience requirement.

### 3.8 Voice / audio / media (1 row in registry)

| App | Update | Proof | Env | Deps | Rollback | Blockers | Lane | Auto-safe? |
|---|---|---|---|---|---|---|---|---|
| Azure Speech SDK JS (`microsoft-cognitiveservices-speech-sdk`, latest **v1.49.0** 2025-03-31) | `npm install microsoft-cognitiveservices-speech-sdk@<v>` against GUI front-end `package.json` | `node -e "console.log(require('microsoft-cognitiveservices-speech-sdk').SpeechSDK?.SpeechConfig)"` + `voice.py` `/voice/tts` 200 | browser (ESM) + Node 18+ (worker) | subscription key + region OR Entra/AAD token (`G:\private\.env` `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`) | `npm install <prev>` + lockfile revert | v1.47 removed speaker/intent recognition; v1.46 deprecated `EndSilenceTimeoutMs`; runtime path uses Azure Speech REST not SDK JS | coding-agents lane (front-end) | **patch yes**; **gated minor** (test STT+TTS round-trip) |

### 3.9 Library / Materials / Hardware / Utilities / Research (7 rows)

| App | Section | Update | Proof | Lane | Auto-safe? |
|---|---|---|---|---|---|
| Manyfold | library | `docker compose pull` pinned tag (latest `ghcr.io/manyfold3d/manyfold:v0.139.2` 2026-05-08) | `curl :3214/up` Rails health + `:/api/v0/models` 200 | print-farm/library lane | **patch yes**; **minor: hold for backup snapshot** (no documented DB-rollback) |
| Open Filament Database | materials | `git pull` (data-only); license `unknown` | `git rev-parse HEAD` matches upstream + `jq .` parses | materials/data lane | **yes** (data-only, idempotent) once schema linter passes |
| 3D Box Generator | utilities | `git pull` reference clone (license `unknown`) | `git log -1` + (optional) Vite build smoke | utilities lane | **yes** (reference-only) |
| Awesome 3D Printing | research | `git pull` curated Markdown index (license **CC0-1.0**) | `git log -1` + `wc -l README.md` | research lane | **yes — fully auto-update safe** |
| Awesome Extruders | hardware | `git pull` catalog README (license `unknown`; `verify_source_before_claiming`) | `git log -1` | hardware-catalog lane | **yes** (catalog-only) |
| BoxTurtle | hardware | `git pull` hardware-design repo (license GPL-3.0; priority `future`) | `git rev-parse HEAD` (current `4c6a143ead69`) | hardware-catalog lane | **yes** (reference-only) |
| EnragedRabbitProject | hardware | `git pull` (license GPL-3.0); **brief disagrees with audit on remote** (Enraged-Rabbit-Community/ERCF_v2 vs EtteGit/EnragedRabbitProject — reconcile) | `git rev-parse HEAD` (current `fb9a6c7daaf8`) | hardware-catalog lane | **yes** (reference) **after remote reconciled** |

### 3.10 LangChain + LangGraph + Kiln (3 source-reference agent rows)

| App | Update | Proof | Lane | Auto-safe? |
|---|---|---|---|---|
| LangChain (langchain-ai/langchain, MIT) | `git pull` reference; if elevated to runtime: `pip install -U langchain` pinned | `git rev-parse HEAD` + (if installed) `import langchain` | agents lane | **reference: yes**; runtime: gated |
| LangGraph (langchain-ai/langgraph, MIT) | same as LangChain (priority `primary` — intended runtime) | `git rev-parse HEAD` + `import langgraph` | agents lane | **reference: yes**; runtime: gated with replay tests |
| Kiln (codeofaxel/Kiln per audit JSON, NOT kiln-ai/kiln; license `unknown`; `verify_source_before_claiming`) | `git pull` reference clone | `git rev-parse HEAD` | agents-research lane | **no** until source identity reconciled |

## 4. System dependency matrix

|  | Windows native | WSL2 | Docker (slim) | Docker (ubuntu:24.04 fuller) | Linux VPS |
|---|---|---|---|---|---|
| **Slicer desktop apps** | Y | partial[1] | N | N | N |
| **Slicer CLI engines** | Y | Y | Y | Y | Y |
| **Modeler desktop apps** | Y | partial[1] | partial[2] | partial[2] | partial[3] |
| **Modeler Python pkgs** | Y | Y | Y | Y | Y |
| **3D-gen GPU workers** | partial[4] | Y[5] | Y[5] | Y[5] | Y[5] |
| **Print-farm services** | partial[6] | Y | Y | Y | Y (canonical) |
| **Firmware compile** | partial | Y | Y | Y | Y |
| **Firmware FLASH** | NEVER | NEVER | NEVER | NEVER | NEVER |
| **Coding agents** (Hermes/OpenCode/OpenHands) | Y[7] | Y | partial[7] | Y | Y |
| **MCP servers** | Y | Y | Y | Y | Y |
| **Voice / audio** | partial[8] | partial[8] | N | partial[8] | Y[8] |
| **Browser/UI web apps** | Y | Y | Y | Y | Y |

**Footnotes:**
- **[1]** Desktop apps under WSL2 work via WSLg (Win11 native) but lose GPU acceleration for Vulkan/Metal-equivalent paths; OpenSCAD CSG re-rendering and Blender Cycles GPU hit a hard wall.
- **[2]** Headless modeler Docker is `xvfb`-only — no live viewport; FreeCAD/Blender batch-only.
- **[3]** Linux VPS: same caveat as [2]; need `xvfb-run` wrapper; no GUI.
- **[4]** Windows native CUDA OK only with NVIDIA cards + matching CUDA toolkit; AMD ROCm path is broken on Win.
- **[5]** Requires `nvidia-container-toolkit` (Docker) or WSL2 CUDA passthrough. CPU fallback impractical for TRELLIS/Hunyuan.
- **[6]** Klipper itself runs on Linux only (kernel scheduling deps). Moonraker/Mainsail run on Windows with caveats. OctoPrint Python OK on Windows. **Klipper-on-Windows: NOT supported.**
- **[7]** Coding agents on Docker hit the systemd / D-Bus gap when the agent expects to spawn user services. Mitigation: `docker run --init --tmpfs /run + dumb-init`, OR use `ubuntu:24.04` fuller container with `dbus-user-session` + linger (Batch 1 Agent 2's Dockerfile sketch).
- **[8]** Voice/audio in containers requires PulseAudio install + host audio passthrough (`--device /dev/snd` + PA socket bind). Browser-side Speech SDK JS works everywhere a browser runs.

## 5. Cross-cutting issues (top 10)

1. **License `unknown` on 8 rows blocks auto-update safety**: Strec3D, FLSUN Slicer, Kiln, Awesome Extruders, BoxTurtle, ComfyUI TRELLIS Wrapper, 3D Box Generator, Open Filament Database. Per project's no-paid-services / open-source-only policy, every "auto-update safe" verdict for these is conditional on a license verification PR. **Action**: add a `license_verified: bool` field to schema; refuse auto-update when `false`.
2. **`tests/e2e/` conftest sys.modules contamination** (root cause of v0.13.0 lane fail) — solved by upstream's `--ignore=tests/e2e` path filter (Batch 1 Agent 1, 3 receipts). Phase 4 patch in `agent_updates.py` aligns our gate.
3. **Marker filtering happens AFTER conftest import** — `--ignore` operates at collection time, before conftest body runs (Batch 1 Agent 3 receipt). Marker-only filtering can never fix mock leakage.
4. **Container kernel-string leak** (Docker Desktop on Windows uses WSL2 kernel for ALL Linux containers; `is_wsl()` returns True inside containers). Detection logic must use `/proc/1/cgroup` or `/.dockerenv` to distinguish "WSL host" from "container in WSL host".
5. **Web-app reference cache-bust gap** — browser-served apps (Fluidd, Mainsail, Comfy Frontend, Manyfold UI, Kiri:Moto, 3D Box Generator, Kiln) update by image-tag rotation but front-end shell may serve stale `service-worker.js` to existing tabs. **Action**: every web-app update lane must emit `Clear-Site-Data` directive or bump query-string cache-buster after `docker compose up -d`.
6. **Verify-source policy collides with audit-discovered remotes** (7 rows) — Kiln→codeofaxel, BoxTurtle→ArmoredTurtle, ERCF→EtteGit, Awesome Extruders→SartorialGrunt0 etc. The auto-update lane will pull from the WRONG upstream until reconciled. **Action**: block all hardware/research lanes until human confirms remote identity.
7. **Firmware FLASH safety not enforced in CI** — all 6 firmware rows carry `safety: no_flash_without_explicit_approval` but no CI gate asserts no auto-update path triggers `klipper-flash`/`avrdude`/`platformio run -t upload`. **Action**: add deny-listed-command gate in update orchestrator + unit test that fails if any firmware-row update lane references a flash target.
8. **Klipper double registration** — same repo registered as BOTH `print_farm/klipper` (service) AND `firmware/klipper` (renamed `firmware_klipper`). Bumping host without re-flashing MCU breaks wire protocol. **Action**: paired-update gate.
9. **Code vs weights** for 3D-gen — every gpu_worker has TWO update vectors (Python source + model checkpoints). Update lanes must propagate this split — mismatched code+weights bricks generation. **Action**: `code_sha + weights_revision` tuple in every gen3d update record.
10. **Codecov 2021-class env exfiltration risk** (Batch 1 Agent 6 receipt 2) — if `_check_external` ever switches to `shell=True` or logs `os.environ`, we replicate the CVE. **Action**: unit test that asserts env never logged in proof events.

## 6. Research receipts (consolidated)

### 6.1 Hermes Agent upstream CI (Agent 1)
- **Primary**: https://raw.githubusercontent.com/NousResearch/hermes-agent/main/.github/workflows/tests.yml — upstream uses path-based `--ignore=tests/integration --ignore=tests/e2e` not marker filter; Python 3.11 via uv; cred envs blanked. **Impact: Phase 4 patch must mirror exactly.**
- **Cross-project**: https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/.github/workflows/unit_tests.yml — same path-ignore + xdist auto pattern. **Impact: validates pattern; supports keeping `-n auto` (no need to switch to numeric).**
- **Risk**: cleanup commit `66320de52` is 174 commits ahead of v2026.5.7 — won't be in any tagged release until upstream cuts v2026.5.8.

### 6.2 systemd-in-container + audio (Agent 2)
- **Primary**: https://systemd.io/CONTAINER_INTERFACE/ — systemd-as-PID-1 requires `/sys/fs/cgroup` + `--cgroupns=host` + `dbus-user-session` + `STOPSIGNAL SIGRTMIN+3`; **NOT OK to mount sub-hierarchy of cgroups**.
- **Cross-project**: https://github.com/geerlingguy/docker-ubuntu2404-ansible/blob/master/Dockerfile — battle-tested template; mask `systemd-udevd.service` to avoid hang loop in containers; `VOLUME ["/sys/fs/cgroup", "/tmp", "/run"]`; CMD `/lib/systemd/systemd`.
- **Audio**: https://docs.pytest.org/en/stable/how-to/skipping.html — `pytest.importorskip("sounddevice")` is the right pattern for audio runtime tests; 4 failing `TestDetectAudioEnvironment` tests need either runtime probe with `skipif` or fixture-level mock.

### 6.3 pytest / xdist / test isolation (Agent 3)
- **Primary**: https://docs.pytest.org/en/stable/example/pythoncollection.html#ignore-paths-during-test-collection + https://docs.pytest.org/en/stable/reference/customize.html — `--ignore` operates at collection-time (BEFORE conftest import); `-m` operates at selection-time (AFTER). For `sys.modules` contamination, only `--ignore` solves it.
- **Cross-project (production reference)**: https://github.com/numpy/numpy/blob/main/numpy/conftest.py — clean pattern: `try: import scipy_doctest … except ModuleNotFoundError:` (no sys.modules mutation); markers via `pytest_configure(config)` not module-level side effects.
- **xdist**: https://pytest-xdist.readthedocs.io/en/stable/distribution.html — `-n 0` = fully serial (NO worker subprocess); `PYTEST_XDIST_AUTO_NUM_WORKERS=<int>` env or `pytest_xdist_auto_num_workers(config)` hook for deterministic CI worker counts.

### 6.4 Cross-project updaters (Agent 4)
- **OpenHands**: https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/runtime/utils/runtime_build.py — triple-tag: `oh_v{ver}_{lockhash}` + `oh_v{ver}_{lockhash}_{sourcehash}`; lockhash = MD5(base+pyproject.toml+poetry.lock)[:16]; sourcehash = MD5(source_dir)[:16]. **Adopt verbatim** — single biggest perf win for 60-app lane.
- **OpenCode**: https://github.com/sst/opencode/blob/dev/.github/workflows/publish.yml — multi-channel + timestamp-preview (`0.0.0-{channel}-{timestamp}`); 7-platform/arch matrix. Note: Azure Trusted Signing is a paid service — substitute Sigstore + GitHub Attestations.
- **uv anti-pattern**: https://github.com/astral-sh/uv/issues/12816 — `uv self update` can self-uninstall and brick reinstall. Lesson: **never mutate the live binary in-place**; always swap-via-symlink with snapshot.
- **VSCode UpdateMode**: https://code.visualstudio.com/docs/enterprise/updates — 4-state enum `default | start | manual | none` + per-extension `extensions.autoUpdate` toggle. **Map to our 60-app dashboard verbatim** but JSON-first (UI is thin shell).

### 6.5 Manyfold + Azure Speech SDK JS (Agent 5)
- **Manyfold**: https://github.com/manyfold3d/manyfold — latest **v0.139.2** 2026-05-08; 221 releases; **no documented DB-rollback procedure**; pre-update gate must `pg_dump` snapshot.
- **Azure Speech SDK JS**: https://github.com/microsoft/cognitive-services-speech-sdk-js/releases — latest **v1.49.0** 2025-03-31; v1.47.0 removed speaker/intent recognition; v1.46 deprecated `EndSilenceTimeoutMs`. **Hermes3D voice route uses Azure Speech REST server-side, not the JS SDK** — SDK is browser-only reference.

### 6.6 Security (Agent 6)
- **Primary**: https://owasp.org/www-project-top-10-ci-cd-security-risks/ — CICD-SEC-1 "Insufficient Flow Control Mechanisms" maps directly to our staged update lane. **Implication**: skip path returning 200/skipped is a fake-pass surface; must return `requires_confirmation`.
- **Cross-project**: https://about.codecov.io/apr-2021-post-mortem/ — modified CI step exfiltrated `env` to attacker for 23k customers over 60 days. **Implication**: unit-test that `_check_external` never logs `os.environ`.

## 7. Recommended Phase 4 patch v2 (security-hardened)

After Batch 1 Agent 6's 5 must-fix items, the original Phase 4 patch (verified in-container, `5532 → 20734` passing tests) needs these **additional** guards before landing in source. The proposed final state of `_run_update_checks` (in `agent_updates.py`) is:

```python
# In _run_update_checks pytest gate branch:
if os.environ.get("HERMES_AGENT_RUN_PYTEST") == "1" and tests_dir.exists():
    workers_env = os.environ.get("HERMES_AGENT_PYTEST_WORKERS", "auto").strip()
    diagnostic_mode = os.environ.get("HERMES_AGENT_DIAGNOSTIC", "").strip() == "1"
    # Reject sub-2 worker counts in production (Agent 6 must-fix #2)
    if not diagnostic_mode and workers_env in ("0", "1"):
        raise HTTPException(status_code=400, detail=(
            "HERMES_AGENT_PYTEST_WORKERS must be >=2 in production; "
            "set HERMES_AGENT_DIAGNOSTIC=1 to override."
        ))
    maxfail = "5" if diagnostic_mode else "1"  # Agent 6 must-fix #4: maxfail=1 default
    pytest_args = ["python", "-m", "pytest", str(tests_dir), "-m", "not integration",
                   "--ignore=tests/integration", "--ignore=tests/e2e",  # mirror upstream tests.yml
                   "--maxfail=" + maxfail, "-q", "-n", workers_env]
    checks.append(_check_external(repo, "python pytest non-integration", pytest_args, timeout=600))
elif tests_dir.exists():
    # Agent 6 must-fix #1: skip path returns requires_confirmation, NOT skipped/OK
    checks.append({
        "name": "python pytest non-integration",
        "status": "fail",  # was "skipped" — fail-closed
        "output": (
            "REQUIRES_CONFIRMATION: HERMES_AGENT_RUN_PYTEST not set to '1'. "
            "Pytest gate cannot certify update without explicit opt-in. "
            "Set HERMES_AGENT_RUN_PYTEST=1 or use the staged endpoint with run_checks=true."
        ),
    })
```

Plus a **meta-test** (Agent 6 must-fix #3) in `04_testing/pytest/unit/test_agent_updates.py` that fetches upstream `tests.yml` via the GitHub API and asserts it still contains `--ignore=tests/integration` and `--ignore=tests/e2e`. If upstream removes those flags, our `--ignore` is now hiding e2e regressions — fail loud.

Plus a **firmware archive-dir audit** (Agent 6 must-fix #5) in the schema validator — every firmware row's `rollback_method` must name a real `firmware_archive_dir` policy.

## 8. Compliance with the speed rule

The user requires updates feel instant via:

| Speed dimension | Pattern source | Status |
|---|---|---|
| **App update profiles precomputed** | THIS DOC (60 rows) | Initial pass landed; per-app sub-files pending |
| **Dependency containers cached** | OpenHands triple-tag (`oh_v{ver}_{lockhash}_{sourcehash}`) | To implement in Batch 4 |
| **Quick smoke before full proof** | OpenCode multi-stage publish (build → sign → publish) | Batch 4 |
| **Background async full proof** | Async fan-out + per-app proof matrix | Batch 4 |
| **Pre-existing rollback snapshot** | `_create_backup` already exists in `agent_updates.py` (mature for Hermes Agent); needs generalization to all 60 apps | Batch 4 |
| **Live-status UI not blocking** | VSCode `UpdateMode` enum + non-modal status | Future Task Monitor UI v3 lane (deferred behind RC v2) |
| **Per-app auto-update toggle** | VSCode `extensions.autoUpdate` (JSON-first) | Schema work in Batch 3 |
| **Per-app version pin** | uv versioned-URL install + OpenCode channel selector | Schema work in Batch 3 |

## 9. Lanes (where to put each update)

- **Lane A (Service-class)**: ComfyUI, Manyfold, Open Filament Database, FDM Monster, OctoPrint, Moonraker, Klipper service, Mainsail, Fluidd. Auto-safe with rollback if Docker-tag pinned + DB snapshot.
- **Lane G (GPU-worker)**: Hunyuan3D 2.1, Microsoft TRELLIS.2, TripoSR, ComfyUI TRELLIS Wrapper. Manual approval, staging GPU smoke test, HITL on weight/license re-verify.
- **Lane R (Reference)**: All `*_reference`/`source_reference`/`catalog_reference`/`hardware_reference` rows. Pin to upstream release tag; no nightlies.
- **Lane F (Firmware-flash)**: All 6 firmware rows. **NEVER auto-flash.** Vendor-or-user explicit flash only.
- **Lane S (Source-modelers, Python-pkg tier)**: trimesh, manifold3d (already pinned in `requirements.txt`), build123d, CadQuery, numpy-stl, Open3D, pymesh→pymeshfix, plus the modeler desktop apps with parallel-install support.
- **Lane H (Hermes Agent staged endpoint)**: only Hermes Agent. Phase 4 patch v2 (§7).
- **Lane M (MCP servers)**: hermes3d-locks (highest-trust, truth-gate covered); blender-mcp variants (manual confirm); Claude Code bundled (defer to Claude Code).

## 10. Status legend (per app)

Following the user's "select what apps to update and what apps to exclude" requirement, every app gets one of:
- `auto_update_enabled` (default on for `Lane A` + `Lane R` + `Lane S` patch tags + `Awesome 3D Printing`)
- `auto_update_disabled_user_pin` (user wants this app frozen)
- `auto_update_blocked_license_unknown` (the 8 unknown-license rows)
- `auto_update_blocked_verify_source` (the 7 verify_source rows)
- `auto_update_blocked_safety` (all 6 firmware rows)
- `auto_update_manual_confirm_per_release` (slicers with profile-format risk; OctoPrint with plugin compat; Hermes Agent v0.13.0+; OpenHands+OpenCode until pre-flight wired)
- `pin_only_no_update` (Slic3r, Strec3D, OctoFarm, BotQueue, KlipperScreen)

## 11. What's still open

- **Per-section sub-files**: split this doc into `handoffs/60-apps/<section>.md` files for the dashboard to fetch on-demand (one HTTP call per section instead of one big doc). Defer to Batch 4.
- **Schema**: add `license_verified`, `update_status` (enum from §10), `weights_revision` (for gen3d), `firmware_archive_dir` (for firmware), `proof_redaction_required` to the registry YAML. Defer to Batch 4.
- **Hermes Agent v0.13.0**: still formally deferred per §3.6. Resume lane only when upstream tags v2026.5.8+ AND lands `is_container()/is_wsl()` skipif decorators (issue #22420).
- **RC v2 commit 1** done at SHA 45e9299 on `claude/recovery-controller-v2`; commits 2-5 deferred behind this audit + the v0.13.0 resolution.

## 12. MCP evidence chain

Audit lane head: `ev_ff307000983c3f4b` (Cplus formal-defer summary, chained from lane A → lane B → lane Cplus → lane Cplus-py311+docker).

Batch 1 sub-agent IDs (read-only research, no mutations):
- Agent 1 (upstream CI): `a4529397487c4bad2`
- Agent 2 (Docker/systemd/audio): `a5583bf77632ba274`
- Agent 3 (pytest/xdist): `a110cc646f0ec11e3`
- Agent 4 (cross-project updaters): `ae0ecc8bb669d9c78`
- Agent 5 (gap auditor): `a2392ce826cb9e40f`
- Agent 6 (security/proof): `a9c9a652361113b2e`

Plus prior 6-agent matrix slices (slicers/modelers/3D-gen/printer-firmware/coding-agents/MCP) from earlier in this conversation.
