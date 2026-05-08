# Source OS Module Registry — 60 Apps

Canonical index of every app the Hermes3D Source OS module loader knows about, extracted directly from the registry the loader actually parses at runtime.

## Methodology

Sourced from (in priority order, exactly how `load_modules.py` resolves them):

1. **Primary YAML registry** — `G:\Github\Hermes3D\Hermes3D-GUI-Wiring-Contract-Kit\03_REPO_REGISTRY\external_repos_registry.yaml` (439 lines, 11 sections, 60 module rows).
2. **Fallback truth-audit JSON** — `G:\Github\h3d-gui-wiring-codex\03_implementation\proof\SOURCE_REGISTRY_TRUTH_AUDIT.json` (used when the YAML is missing; also contains 60 module rows, validated independently).
3. **Loader logic** — `G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\db\load_modules.py` (`_parse_registry`, `LAUNCH_KIND_OVERRIDES`, `SOURCE_OVERRIDES`, `SECTION_TARGET_DIRS`).
4. **Schema** — `G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\db\schema.sql` (`modules` table columns: id, display_name, section, priority, license, repo_url, local_path, install_state, install_progress, detected_version, health, launch_kind, bridge_tasks).
5. **API route** — `G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\api\routes\modules.py`.
6. **h3dos-codex integration folders** — directory listing of `G:\Github\h3dos-codex-*` (5 folders found: blender-cli, fluidd, octoprint, prusaslicer, triposr).

The loader reconciles each YAML row with `source_manifest.json` and `SOURCE_OVERRIDES`, then writes one SQLite row per `unique_id` (collisions get prefixed by section, e.g. the duplicate `klipper` in `print_farm` + `firmware` becomes `firmware_klipper`).

## Total count

**60 modules** across 11 sections. Verified against both the YAML registry and the truth-audit JSON; both agree.

Section breakdown: modelers 13, slicers 11, print_farm 10, agents 7, firmware 6, three_d_generation 6, hardware 3, library 1, materials 1, research 1, utilities 1.

Note: `klipper` is registered in both `print_farm` and `firmware` (separate rows with different `launch_kind` and safety semantics). The loader gives the second occurrence the unique id `firmware_klipper`. Total distinct YAML keys = 59; total distinct module rows in DB = 60.

## Verifier-type legend

Derived from `launch_kind` (with `LAUNCH_KIND_OVERRIDES` applied):

| Verifier type | launch_kind values | Detection method |
|---|---|---|
| Desktop / CLI app | `desktop_app`, `desktop_or_cli`, `cli_or_python_worker`, `cli_worker` | CLI binary on PATH or known install dir |
| Service | `service` | HTTP health endpoint |
| Python worker | `python_worker` | Python import / venv detection |
| GPU worker | `gpu_worker` | Service + CUDA / GPU probe |
| Web app | `web_app` | HTTP serve + browser launch |
| NPM package | `npm_package` | `node_modules` / package.json |
| Reference only | `*_reference`, `reference`, `firmware_source`, `catalog_reference`, `hardware_reference`, `source_reference`, `touch_ui_reference`, `web_app_reference`, `rust_library_reference`, `service_reference` | Source clone only, no runtime |
| Unknown | `unknown` | Pending classification |

## Master table

| App | Category | launch_kind / Verifier | Install hint (repo) | h3dos-codex folder | Status (priority) |
|---|---|---|---|---|---|
| BambuStudio | slicers | desktop_or_cli (override) | github.com/bambulab/BambuStudio | — | reference |
| Ultimaker Cura | slicers | desktop_app | github.com/Ultimaker/Cura | — | secondary |
| CuraEngine | slicers | cli_worker | github.com/Ultimaker/CuraEngine | — | secondary |
| FLSUN Slicer | slicers | desktop_app | Flsun3d/FlsunSlicer (override) | — | profile-first |
| Kiri:Moto / GridSpace | slicers | web_app | github.com/GridSpace/grid-apps | — | reference |
| MatterControl | slicers | desktop_app (override) | github.com/MatterHackers/MatterControl | — | reference |
| OrcaSlicer | slicers | desktop_app | github.com/SoftFever/OrcaSlicer | — | primary |
| PrusaSlicer | slicers | desktop_app | github.com/prusa3d/PrusaSlicer | h3dos-codex-prusaslicer | primary |
| Slic3r | slicers | desktop_or_cli (override) | github.com/slic3r/Slic3r | — | reference |
| Strec3D | slicers | cli_worker (override) | (vendor verify) | — | research |
| SuperSlicer | slicers | desktop_or_cli (override) | github.com/supermerill/SuperSlicer | — | reference |
| Blender | modelers | desktop_app | github.com/blender/blender | h3dos-codex-blender-cli | primary |
| build123d | modelers | python_worker | github.com/gumyr/build123d | — | primary |
| CadQuery | modelers | python_worker | github.com/CadQuery/cadquery | — | primary |
| FreeCAD | modelers | desktop_app | github.com/FreeCAD/FreeCAD | — | secondary |
| Manifold | modelers | cli_or_python_worker | github.com/elalish/manifold | — | primary |
| MeshLab | modelers | desktop_or_cli | github.com/cnr-isti-vclab/meshlab | — | reference |
| numpy-stl | modelers | python_worker | github.com/WoLpH/numpy-stl | — | candidate |
| Open3D | modelers | python_worker | github.com/isl-org/Open3D | — | candidate |
| OpenSCAD | modelers | desktop_or_cli | github.com/openscad/openscad | — | primary |
| pymesh | modelers | python_worker | pyvista/pymeshfix (override) | — | candidate |
| SolveSpace | modelers | desktop_app | github.com/solvespace/solvespace | — | reference |
| trimesh | modelers | python_worker | github.com/mikedh/trimesh | — | primary |
| truck | modelers | rust_library_reference | github.com/ricosjp/truck | — | research |
| FDM Monster | print_farm | service | github.com/fdm-monster/fdm-monster | — | primary |
| Fluidd | print_farm | web_app | github.com/fluidd-core/fluidd | h3dos-codex-fluidd | reference |
| Klipper | print_farm | service | github.com/Klipper3d/klipper | — | core-runtime |
| KlipperScreen | print_farm | touch_ui_reference | github.com/KlipperScreen/KlipperScreen | — | reference |
| Mainsail | print_farm | web_app | github.com/mainsail-crew/mainsail | — | reference |
| Moonraker | print_farm | service | github.com/Arksine/moonraker | — | primary |
| OctoFarm | print_farm | service_reference | github.com/OctoFarm/OctoFarm | — | reference |
| OctoPrint | print_farm | service | github.com/OctoPrint/OctoPrint | h3dos-codex-octoprint | secondary |
| BotQueue | print_farm | service_reference | (verify source) | — | reference |
| Printrun | print_farm | desktop_or_cli | kliment/Printrun (override) | — | secondary |
| Klipper (firmware) | firmware | service (override: firmware_klipper) | github.com/Klipper3d/klipper | — | core-runtime |
| Marlin | firmware | firmware_source (override) | github.com/MarlinFirmware/Marlin | — | secondary |
| Prusa Firmware | firmware | firmware_source (override) | github.com/prusa3d/Prusa-Firmware | — | secondary |
| Repetier Firmware | firmware | firmware_source (override) | (verify source) | — | reference |
| RepRapFirmware | firmware | firmware_source (override) | github.com/Duet3D/RepRapFirmware | — | reference |
| Smoothieware | firmware | firmware_source (override) | github.com/Smoothieware/Smoothieware | — | reference |
| ComfyUI | three_d_generation | service | github.com/comfyanonymous/ComfyUI | — | primary |
| ComfyUI Frontend | three_d_generation | web_app_reference | github.com/Comfy-Org/ComfyUI_frontend | — | reference |
| ComfyUI TRELLIS.2 Wrapper | three_d_generation | service | (verify source) | — | primary |
| Tencent Hunyuan3D 2.1 | three_d_generation | gpu_worker | github.com/Tencent-Hunyuan/Hunyuan3D-2 | — | secondary |
| Microsoft TRELLIS.2 | three_d_generation | gpu_worker | github.com/microsoft/TRELLIS | — | primary |
| TripoSR | three_d_generation | gpu_worker | github.com/VAST-AI-Research/TripoSR | h3dos-codex-triposr | fast-preview |
| Azure Speech SDK JS | agents | npm_package | github.com/microsoft/cognitive-services-speech-sdk-js | — | primary |
| Blender MCP Candidates | agents | python_worker (override) | ahujasid/blender-mcp (override) | — | reference |
| Hermes Agent (NousResearch) | agents | python_worker | github.com/NousResearch/hermes-agent | — | primary |
| Kiln | agents | web_app_reference (override) | (verify source) | — | research |
| LangChain | agents | source_reference (override) | github.com/langchain-ai/langchain | — | reference |
| LangGraph | agents | source_reference (override) | github.com/langchain-ai/langgraph | — | primary |
| Model Context Protocol | agents | npm_package (override) | github.com/modelcontextprotocol/specification | — | primary |
| Manyfold | library | service | github.com/manyfold3d/manyfold | — | primary |
| Open Filament Database | materials | service | github.com/OpenFilamentCollective/open-filament-database | — | primary |
| Awesome Extruders | hardware | catalog_reference (override) | (verify source) | — | catalog |
| BoxTurtle | hardware | hardware_reference (override) | (verify source) | — | future |
| EnragedRabbitProject | hardware | hardware_reference (override) | github.com/Enraged-Rabbit-Community/ERCF_v2 | — | future |
| 3D Box Generator | utilities | web_app_reference | github.com/javisperez/box-stl-generator | — | reference |
| Awesome 3D Printing | research | reference | github.com/ad-si/awesome-3d-printing | — | catalog |

## Per-category sections

The brief asked for SLICERS, MODELERS, FIRMWARE, PRINT-FARM, 3D-GENERATION, AGENT-CLI, MISC. The registry has more granular sections; the mapping below absorbs `library`, `materials`, `hardware`, `utilities`, `research` into MISC.

### SLICERS (11)
BambuStudio, Ultimaker Cura, CuraEngine, FLSUN Slicer, Kiri:Moto / GridSpace, MatterControl, OrcaSlicer, PrusaSlicer, Slic3r, Strec3D, SuperSlicer.

Implementation folders: `h3dos-codex-prusaslicer` (PrusaSlicer integration only).

### MODELERS (13)
Blender, build123d, CadQuery, FreeCAD, Manifold, MeshLab, numpy-stl, Open3D, OpenSCAD, pymesh, SolveSpace, trimesh, truck.

Implementation folders: `h3dos-codex-blender-cli` (Blender integration).

### FIRMWARE (6)
Klipper (firmware row), Marlin, Prusa Firmware, Repetier Firmware, RepRapFirmware, Smoothieware.

Implementation folders: none. All firmware modules are flagged `safety: no_flash_without_explicit_approval` and treated as source references.

### PRINT-FARM (10)
FDM Monster, Fluidd, Klipper, KlipperScreen, Mainsail, Moonraker, OctoFarm, OctoPrint, BotQueue, Printrun.

Implementation folders: `h3dos-codex-fluidd`, `h3dos-codex-octoprint`.

### 3D-GENERATION (6)
ComfyUI, ComfyUI Frontend, ComfyUI TRELLIS.2 Wrapper, Tencent Hunyuan3D 2.1, Microsoft TRELLIS.2, TripoSR.

Implementation folders: `h3dos-codex-triposr`.

### AGENT-CLI (7)
Azure Speech SDK JS, Blender MCP Candidates, Hermes Agent (NousResearch), Kiln, LangChain, LangGraph, Model Context Protocol.

Implementation folders: none in the `h3dos-codex-*` namespace. Hermes Agent is checked out at `G:\Github\hermes-agent-fresh` (per `SOURCE_OVERRIDES`).

### MISC (7)
- **library** (1): Manyfold
- **materials** (1): Open Filament Database
- **hardware** (3): Awesome Extruders, BoxTurtle, EnragedRabbitProject
- **utilities** (1): 3D Box Generator
- **research** (1): Awesome 3D Printing

## h3dos-codex-* coverage summary

5 of 60 modules have a dedicated `h3dos-codex-*` integration folder on disk (8.3% coverage):

| Folder | Module |
|---|---|
| `G:\Github\h3dos-codex-blender-cli` | Blender |
| `G:\Github\h3dos-codex-fluidd` | Fluidd |
| `G:\Github\h3dos-codex-octoprint` | OctoPrint |
| `G:\Github\h3dos-codex-prusaslicer` | PrusaSlicer |
| `G:\Github\h3dos-codex-triposr` | TripoSR |

The remaining 55 modules currently rely on the generic loader resolving them via `source-lab/sources/<section>/<safe-name>` — install state is determined by `inspect_source_path()` (clone presence + git short hash), not a hand-tuned integration.

## SVG diagram — 60-app categorized treemap

Color-coded by verifier type. ~900x600 viewport.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600" width="900" height="600" font-family="Segoe UI, Arial, sans-serif">
  <style>
    .title { font-size: 16px; font-weight: 700; fill: #111; }
    .cat { font-size: 11px; font-weight: 700; fill: #222; }
    .lbl { font-size: 9px; fill: #fff; }
    .lblB { font-size: 9px; fill: #111; }
    .legend { font-size: 10px; fill: #222; }
    rect.cell { stroke: #fff; stroke-width: 1.2; }
    rect.box { fill: none; stroke: #888; stroke-width: 1; }
  </style>
  <rect width="900" height="600" fill="#fafafa"/>
  <text x="20" y="24" class="title">Hermes3D Source OS — 60 Modules by Category & Verifier</text>
  <text x="20" y="42" class="legend">Color = launch_kind / verifier type. Cell label = module id.</text>

  <!-- Legend -->
  <g transform="translate(20,52)">
    <rect x="0"   y="0" width="14" height="14" fill="#1f77b4"/><text x="20" y="11" class="legend">desktop / CLI</text>
    <rect x="120" y="0" width="14" height="14" fill="#2ca02c"/><text x="140" y="11" class="legend">service</text>
    <rect x="210" y="0" width="14" height="14" fill="#9467bd"/><text x="230" y="11" class="legend">python_worker</text>
    <rect x="330" y="0" width="14" height="14" fill="#d62728"/><text x="350" y="11" class="legend">gpu_worker</text>
    <rect x="430" y="0" width="14" height="14" fill="#17becf"/><text x="450" y="11" class="legend">web_app</text>
    <rect x="520" y="0" width="14" height="14" fill="#bcbd22"/><text x="540" y="11" class="legend">npm_package</text>
    <rect x="630" y="0" width="14" height="14" fill="#7f7f7f"/><text x="650" y="11" class="legend">reference / source</text>
    <rect x="780" y="0" width="14" height="14" fill="#ff7f0e"/><text x="800" y="11" class="legend">firmware_source</text>
  </g>

  <!-- SLICERS row: y=80..170, full width -->
  <g transform="translate(20,80)">
    <rect class="box" x="0" y="0" width="860" height="90"/>
    <text x="6" y="-2" class="cat">SLICERS (11)</text>
    <!-- 11 cells, ~78 wide -->
    <rect class="cell" x="0"   y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="4" y="48">BambuStudio</text>
    <rect class="cell" x="78"  y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="82" y="48">Cura</text>
    <rect class="cell" x="156" y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="160" y="48">CuraEngine</text>
    <rect class="cell" x="234" y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="238" y="48">FLSUN Slicer</text>
    <rect class="cell" x="312" y="2" width="78" height="86" fill="#17becf"/><text class="lblB" x="316" y="48">Kiri:Moto</text>
    <rect class="cell" x="390" y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="394" y="48">MatterControl</text>
    <rect class="cell" x="468" y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="472" y="48">OrcaSlicer</text>
    <rect class="cell" x="546" y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="550" y="48">PrusaSlicer</text>
    <rect class="cell" x="624" y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="628" y="48">Slic3r</text>
    <rect class="cell" x="702" y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="706" y="48">Strec3D</text>
    <rect class="cell" x="780" y="2" width="78" height="86" fill="#1f77b4"/><text class="lbl" x="784" y="48">SuperSlicer</text>
  </g>

  <!-- MODELERS row: y=185..275 -->
  <g transform="translate(20,185)">
    <rect class="box" x="0" y="0" width="860" height="90"/>
    <text x="6" y="-2" class="cat">MODELERS (13)</text>
    <!-- 13 cells, ~66 wide -->
    <rect class="cell" x="0"   y="2" width="66" height="86" fill="#1f77b4"/><text class="lbl" x="4" y="48">Blender</text>
    <rect class="cell" x="66"  y="2" width="66" height="86" fill="#9467bd"/><text class="lbl" x="70" y="48">build123d</text>
    <rect class="cell" x="132" y="2" width="66" height="86" fill="#9467bd"/><text class="lbl" x="136" y="48">CadQuery</text>
    <rect class="cell" x="198" y="2" width="66" height="86" fill="#1f77b4"/><text class="lbl" x="202" y="48">FreeCAD</text>
    <rect class="cell" x="264" y="2" width="66" height="86" fill="#9467bd"/><text class="lbl" x="268" y="48">Manifold</text>
    <rect class="cell" x="330" y="2" width="66" height="86" fill="#1f77b4"/><text class="lbl" x="334" y="48">MeshLab</text>
    <rect class="cell" x="396" y="2" width="66" height="86" fill="#9467bd"/><text class="lbl" x="400" y="48">numpy-stl</text>
    <rect class="cell" x="462" y="2" width="66" height="86" fill="#9467bd"/><text class="lbl" x="466" y="48">Open3D</text>
    <rect class="cell" x="528" y="2" width="66" height="86" fill="#1f77b4"/><text class="lbl" x="532" y="48">OpenSCAD</text>
    <rect class="cell" x="594" y="2" width="66" height="86" fill="#9467bd"/><text class="lbl" x="598" y="48">pymesh</text>
    <rect class="cell" x="660" y="2" width="66" height="86" fill="#1f77b4"/><text class="lbl" x="664" y="48">SolveSpace</text>
    <rect class="cell" x="726" y="2" width="66" height="86" fill="#9467bd"/><text class="lbl" x="730" y="48">trimesh</text>
    <rect class="cell" x="792" y="2" width="66" height="86" fill="#7f7f7f"/><text class="lbl" x="796" y="48">truck</text>
  </g>

  <!-- PRINT-FARM row: y=290..380 -->
  <g transform="translate(20,290)">
    <rect class="box" x="0" y="0" width="860" height="90"/>
    <text x="6" y="-2" class="cat">PRINT-FARM (10)</text>
    <!-- 10 cells, 86 wide -->
    <rect class="cell" x="0"   y="2" width="86" height="86" fill="#2ca02c"/><text class="lbl" x="4" y="48">FDM Monster</text>
    <rect class="cell" x="86"  y="2" width="86" height="86" fill="#17becf"/><text class="lblB" x="90" y="48">Fluidd</text>
    <rect class="cell" x="172" y="2" width="86" height="86" fill="#2ca02c"/><text class="lbl" x="176" y="48">Klipper</text>
    <rect class="cell" x="258" y="2" width="86" height="86" fill="#7f7f7f"/><text class="lbl" x="262" y="48">KlipperScreen</text>
    <rect class="cell" x="344" y="2" width="86" height="86" fill="#17becf"/><text class="lblB" x="348" y="48">Mainsail</text>
    <rect class="cell" x="430" y="2" width="86" height="86" fill="#2ca02c"/><text class="lbl" x="434" y="48">Moonraker</text>
    <rect class="cell" x="516" y="2" width="86" height="86" fill="#7f7f7f"/><text class="lbl" x="520" y="48">OctoFarm</text>
    <rect class="cell" x="602" y="2" width="86" height="86" fill="#2ca02c"/><text class="lbl" x="606" y="48">OctoPrint</text>
    <rect class="cell" x="688" y="2" width="86" height="86" fill="#7f7f7f"/><text class="lbl" x="692" y="48">BotQueue</text>
    <rect class="cell" x="774" y="2" width="86" height="86" fill="#1f77b4"/><text class="lbl" x="778" y="48">Printrun</text>
  </g>

  <!-- FIRMWARE row: y=395..485, half width -->
  <g transform="translate(20,395)">
    <rect class="box" x="0" y="0" width="430" height="90"/>
    <text x="6" y="-2" class="cat">FIRMWARE (6)</text>
    <rect class="cell" x="0"   y="2" width="71" height="86" fill="#2ca02c"/><text class="lbl" x="4" y="48">Klipper(fw)</text>
    <rect class="cell" x="71"  y="2" width="71" height="86" fill="#ff7f0e"/><text class="lbl" x="75" y="48">Marlin</text>
    <rect class="cell" x="142" y="2" width="71" height="86" fill="#ff7f0e"/><text class="lbl" x="146" y="48">Prusa FW</text>
    <rect class="cell" x="213" y="2" width="71" height="86" fill="#ff7f0e"/><text class="lbl" x="217" y="48">Repetier</text>
    <rect class="cell" x="284" y="2" width="71" height="86" fill="#ff7f0e"/><text class="lbl" x="288" y="48">RepRapFW</text>
    <rect class="cell" x="355" y="2" width="75" height="86" fill="#ff7f0e"/><text class="lbl" x="359" y="48">Smoothie</text>
  </g>

  <!-- 3D-GENERATION row: y=395..485, right half -->
  <g transform="translate(465,395)">
    <rect class="box" x="0" y="0" width="415" height="90"/>
    <text x="6" y="-2" class="cat">3D-GENERATION (6)</text>
    <rect class="cell" x="0"   y="2" width="69" height="86" fill="#2ca02c"/><text class="lbl" x="4" y="48">ComfyUI</text>
    <rect class="cell" x="69"  y="2" width="69" height="86" fill="#7f7f7f"/><text class="lbl" x="73" y="48">Comfy FE</text>
    <rect class="cell" x="138" y="2" width="69" height="86" fill="#2ca02c"/><text class="lbl" x="142" y="48">TRELLIS Wrap</text>
    <rect class="cell" x="207" y="2" width="69" height="86" fill="#d62728"/><text class="lbl" x="211" y="48">Hunyuan3D</text>
    <rect class="cell" x="276" y="2" width="69" height="86" fill="#d62728"/><text class="lbl" x="280" y="48">TRELLIS.2</text>
    <rect class="cell" x="345" y="2" width="70" height="86" fill="#d62728"/><text class="lbl" x="349" y="48">TripoSR</text>
  </g>

  <!-- AGENT-CLI row: y=500..570, half width -->
  <g transform="translate(20,500)">
    <rect class="box" x="0" y="0" width="430" height="70"/>
    <text x="6" y="-2" class="cat">AGENT-CLI (7)</text>
    <rect class="cell" x="0"   y="2" width="61" height="66" fill="#bcbd22"/><text class="lbl" x="4" y="38">Azure Spch</text>
    <rect class="cell" x="61"  y="2" width="61" height="66" fill="#9467bd"/><text class="lbl" x="65" y="38">Blender MCP</text>
    <rect class="cell" x="122" y="2" width="61" height="66" fill="#9467bd"/><text class="lbl" x="126" y="38">Hermes Agt</text>
    <rect class="cell" x="183" y="2" width="61" height="66" fill="#7f7f7f"/><text class="lbl" x="187" y="38">Kiln</text>
    <rect class="cell" x="244" y="2" width="61" height="66" fill="#7f7f7f"/><text class="lbl" x="248" y="38">LangChain</text>
    <rect class="cell" x="305" y="2" width="61" height="66" fill="#7f7f7f"/><text class="lbl" x="309" y="38">LangGraph</text>
    <rect class="cell" x="366" y="2" width="64" height="66" fill="#bcbd22"/><text class="lbl" x="370" y="38">MCP spec</text>
  </g>

  <!-- MISC row: y=500..570, right half -->
  <g transform="translate(465,500)">
    <rect class="box" x="0" y="0" width="415" height="70"/>
    <text x="6" y="-2" class="cat">MISC (7)</text>
    <rect class="cell" x="0"   y="2" width="59" height="66" fill="#2ca02c"/><text class="lbl" x="4" y="38">Manyfold</text>
    <rect class="cell" x="59"  y="2" width="59" height="66" fill="#2ca02c"/><text class="lbl" x="63" y="38">Open Filam</text>
    <rect class="cell" x="118" y="2" width="59" height="66" fill="#7f7f7f"/><text class="lbl" x="122" y="38">Awe Extr</text>
    <rect class="cell" x="177" y="2" width="59" height="66" fill="#7f7f7f"/><text class="lbl" x="181" y="38">BoxTurtle</text>
    <rect class="cell" x="236" y="2" width="59" height="66" fill="#7f7f7f"/><text class="lbl" x="240" y="38">EnragedRbt</text>
    <rect class="cell" x="295" y="2" width="59" height="66" fill="#7f7f7f"/><text class="lbl" x="299" y="38">Box Gen</text>
    <rect class="cell" x="354" y="2" width="61" height="66" fill="#7f7f7f"/><text class="lbl" x="358" y="38">Awe 3DP</text>
  </g>

  <text x="20" y="592" class="legend">Source: external_repos_registry.yaml + SOURCE_REGISTRY_TRUTH_AUDIT.json (60 rows). h3dos-codex-* implementation folders: 5 of 60.</text>
</svg>
```
