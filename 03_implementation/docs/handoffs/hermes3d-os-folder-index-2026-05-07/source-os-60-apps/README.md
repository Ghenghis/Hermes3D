# Source OS 60-Apps Index

Canonical index of every app the Hermes3D Source OS module loader knows about, drawn directly from the registry the loader parses at runtime.

- **Total modules:** 60
- **Sections:** 11 (slicers, modelers, print_farm, agents, firmware, three_d_generation, hardware, library, materials, research, utilities)
- **`h3dos-codex-*` integration folders found:** 5 of 60 (blender-cli, fluidd, octoprint, prusaslicer, triposr)

See [REGISTRY.md](./REGISTRY.md) for the master table, methodology, per-category sections, and the full 900x600 treemap.

## Source files (read-only)

- Registry YAML: `G:\Github\Hermes3D\Hermes3D-GUI-Wiring-Contract-Kit\03_REPO_REGISTRY\external_repos_registry.yaml`
- Truth-audit JSON fallback: `G:\Github\h3d-gui-wiring-codex\03_implementation\proof\SOURCE_REGISTRY_TRUTH_AUDIT.json`
- Loader: `G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\db\load_modules.py`
- Schema: `G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\db\schema.sql`
- API route: `G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\api\routes\modules.py`

## Category counts

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 540 320" width="540" height="320" font-family="Segoe UI, Arial, sans-serif">
  <style>
    .t { font-size: 14px; font-weight: 700; fill: #111; }
    .l { font-size: 11px; fill: #222; }
    .v { font-size: 11px; font-weight: 700; fill: #fff; }
    .vB { font-size: 11px; font-weight: 700; fill: #111; }
  </style>
  <rect width="540" height="320" fill="#fafafa"/>
  <text x="16" y="22" class="t">Hermes3D Source OS — Modules per Category (60 total)</text>

  <!-- Bars: max=13 (modelers). Bar width per unit = 26px. Start x = 130. -->
  <!-- modelers 13 -->
  <text x="14" y="55" class="l">modelers</text>
  <rect x="130" y="42" width="338" height="20" fill="#1f77b4"/>
  <text x="472" y="57" class="l">13</text>

  <!-- slicers 11 -->
  <text x="14" y="80" class="l">slicers</text>
  <rect x="130" y="67" width="286" height="20" fill="#1f77b4"/>
  <text x="420" y="82" class="l">11</text>

  <!-- print_farm 10 -->
  <text x="14" y="105" class="l">print_farm</text>
  <rect x="130" y="92" width="260" height="20" fill="#2ca02c"/>
  <text x="394" y="107" class="l">10</text>

  <!-- agents 7 -->
  <text x="14" y="130" class="l">agents</text>
  <rect x="130" y="117" width="182" height="20" fill="#9467bd"/>
  <text x="316" y="132" class="l">7</text>

  <!-- firmware 6 -->
  <text x="14" y="155" class="l">firmware</text>
  <rect x="130" y="142" width="156" height="20" fill="#ff7f0e"/>
  <text x="290" y="157" class="l">6</text>

  <!-- three_d_generation 6 -->
  <text x="14" y="180" class="l">3d_generation</text>
  <rect x="130" y="167" width="156" height="20" fill="#d62728"/>
  <text x="290" y="182" class="l">6</text>

  <!-- hardware 3 -->
  <text x="14" y="205" class="l">hardware</text>
  <rect x="130" y="192" width="78" height="20" fill="#7f7f7f"/>
  <text x="212" y="207" class="l">3</text>

  <!-- library 1 -->
  <text x="14" y="230" class="l">library</text>
  <rect x="130" y="217" width="26" height="20" fill="#2ca02c"/>
  <text x="160" y="232" class="l">1</text>

  <!-- materials 1 -->
  <text x="14" y="255" class="l">materials</text>
  <rect x="130" y="242" width="26" height="20" fill="#2ca02c"/>
  <text x="160" y="257" class="l">1</text>

  <!-- utilities 1 -->
  <text x="14" y="280" class="l">utilities</text>
  <rect x="130" y="267" width="26" height="20" fill="#7f7f7f"/>
  <text x="160" y="282" class="l">1</text>

  <!-- research 1 -->
  <text x="14" y="305" class="l">research</text>
  <rect x="130" y="292" width="26" height="20" fill="#7f7f7f"/>
  <text x="160" y="307" class="l">1</text>
</svg>
```

## Verifier-type quick legend

- desktop / CLI app — blue
- service (HTTP) — green
- python_worker — purple
- gpu_worker — red
- web_app — cyan
- npm_package — olive
- reference / source-only — grey
- firmware_source — orange
