# Bonus13 — Schema / Registry Inconsistency Audit

**Author:** claude-batch2-bonus13 (read-only; no source mutation)
**Date:** 2026-05-09
**Scope:** Cross-check of 3 canonical sources for the 60 Source-OS modules.

## Canonical sources used

1. **YAML-A (loader-primary, 60 entries, 439 lines)** — `G:/Github/Hermes3D/Hermes3D-GUI-Wiring-Contract-Kit/03_REPO_REGISTRY/external_repos_registry.yaml` — this is what `load_modules.py::_registry_path()` actually opens at runtime.
2. **YAML-B (kit v4.1 stub, 14 entries, 152 lines)** — `G:/Github/h3d-gui-wiring-codex/hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml` — the path the brief named, but the loader never reads this.
3. **JSON truth-audit (60 entries)** — `03_implementation/proof/SOURCE_REGISTRY_TRUTH_AUDIT.json`.
4. **Loader (Python overrides)** — `03_implementation/src/hermes3d/db/load_modules.py` — `LAUNCH_KIND_OVERRIDES`, `SOURCE_OVERRIDES`, `SECTION_TARGET_DIRS`.

> **Critical structural finding (above per-row level):** The brief named YAML-B as the "primary YAML registry," but YAML-B is a 14-tool *stub* and is never loaded by the runtime. The actual loader-primary is YAML-A. The two YAMLs disagree on field schema entirely (YAML-B has `tested_versions`, `os_support`, `version_policy`, `install`, `verify`, `adapter`; YAML-A has `priority`, `launch_kind`, `repo_policy`, `safety`, `bridge_tasks`). They are not the same registry under different names — they are two different registries with overlapping but different module sets. `tested_versions` does not appear in YAML-A at all → 60/60 modules fail the `tested_versions present + non-empty` check on the runtime path.

## 1. Inconsistency count summary

| Category | Count | Notes |
|---|---|---|
| repo-mismatch (YAML-A vs JSON) | **7** | including 2 path-suffix collisions (Hunyuan3D-2 vs -2.1, TRELLIS vs TRELLIS.2) |
| launch_kind-mismatch / missing in YAML | **18** | YAML-A omits `launch_kind` and loader injects via `LAUNCH_KIND_OVERRIDES` or default "unknown" |
| license-unknown (YAML or JSON) | **10** | flsun_slicer, strec3d, kiln, blender_mcp_candidates, comfyui_trellis_wrapper, awesome_extruders, botqueue, box_stl_generator, open_filament_database, blender_mcp_candidates (JSON) |
| SPDX-invalid identifiers | **42** | 41 use deprecated bare `GPL-3.0` / `LGPL-3.0` / `AGPL-3.0` / `GPL-2.0` / `LGPL-2.0` instead of `-only`/`-or-later`; 1 free-text "Tencent Hunyuan community license" |
| missing tested_versions | **60/60** | field absent from YAML-A; only 14 entries in YAML-B carry it |
| missing safety flag (firmware) | **0/6** | all 6 firmware rows have `safety: no_flash_without_explicit_approval` (PASS) |
| repo_policy: verify_source_before_claiming present | **9** | flsun_slicer, strec3d, pymesh, botqueue, comfyui_trellis_wrapper, kiln, blender_mcp_candidates, awesome_extruders, boxturtle, repetier_firmware (also flsun + strec use *vendor* variants) — actually **10 incl. variants** |
| dead SECTION_TARGET_DIRS entries | **0/11** | every key resolves to ≥1 module |
| section→unique_id collision (firmware/klipper rename) | **PASS** | JSON correctly emits `firmware_klipper` and `klipper` as separate IDs |
| YAML-B coverage gap (loader-canonical) | **46 modules** | YAML-B has 14/60 modules → 46 modules unrepresented in the v4.1 stub |

## 2. Per-row findings

Format: `<id> | <field> | <YAML-A claim> | <JSON claim> | <severity>`. Rows with no findings omitted.

```
trellis              | repo_url     | microsoft/TRELLIS.git              | microsoft/TRELLIS.2.git              | HIGH
hunyuan3d_2_1        | repo_url     | Tencent-Hunyuan/Hunyuan3D-2.git    | Tencent-Hunyuan/Hunyuan3D-2.1.git    | HIGH
hunyuan3d_2_1        | license      | "Tencent Hunyuan community license"| same                                 | HIGH (non-SPDX)
model_context_protocol| repo_url    | modelcontextprotocol/specification | modelcontextprotocol/modelcontextprotocol | HIGH
enraged_rabbit_project| repo_url    | Enraged-Rabbit-Community/ERCF_v2   | EtteGit/EnragedRabbitProject         | HIGH
orcaslicer           | repo_url     | SoftFever/OrcaSlicer.git           | OrcaSlicer/OrcaSlicer.git            | MED
hermes_agent         | repo_url     | NousResearch/hermes-agent.git      | NousResearch/Hermes-Agent.git        | LOW (case)
flsun_slicer         | license      | unknown + verify_source            | unknown                              | MED
strec3d              | license      | unknown + verify_vendor_source     | unknown                              | MED
strec3d              | launch_kind  | unknown                            | desktop_app (override)               | MED
kiln                 | license      | unknown + verify_source            | unknown                              | MED
kiln                 | launch_kind  | (absent)                           | web_app_reference (override)         | MED
blender_mcp_candidates| license     | unknown + verify_source            | unknown                              | MED
blender_mcp_candidates| repo_url    | (candidates list, no scalar repo)  | ahujasid/blender-mcp.git (override)  | HIGH
comfyui_trellis_wrapper| license    | unknown + verify_source            | unknown                              | MED
botqueue             | license      | unknown + verify_source            | unknown                              | MED
awesome_extruders    | license      | unknown + verify_source            | unknown                              | MED
boxturtle            | repo_url     | (absent: verify_source)            | ArmoredTurtle/BoxTurtle.git          | HIGH
boxturtle            | license      | GPL-3.0                            | GPL-3.0                              | LOW (deprecated SPDX)
box_stl_generator    | license      | unknown                            | unknown                              | MED
open_filament_database| license     | unknown                            | unknown                              | MED
repetier_firmware    | repo_url     | (absent: verify_source)            | repetier/Repetier-Firmware.git       | HIGH
pymesh               | repo_url     | (absent: verify_source)            | pyvista/pymeshfix.git (override)     | HIGH (id≠repo)
flsun_slicer         | repo_url     | (absent: verify_source)            | Flsun3d/FlsunSlicer.git (override)   | HIGH
[ALL 41 GPL/LGPL/AGPL/GPL2 rows] | license | bare deprecated SPDX        | bare deprecated SPDX                 | MED
[ALL 60 rows]        | tested_versions | (absent in YAML-A)              | (absent in JSON)                     | HIGH (no version pinning)
```

## 3. Top 10 critical inconsistencies

1. **`hunyuan3d_2_1` repo divergence.** YAML-A points at `Hunyuan3D-2.git`; JSON at `Hunyuan3D-2.1.git`. The `id` and `display_name` say "2.1" → JSON is correct. **Fix:** update YAML-A repo to `Hunyuan3D-2.1.git`, set `repo_policy: vendor_pinned`.
2. **`trellis` repo divergence.** YAML-A `TRELLIS.git`; JSON `TRELLIS.2.git`. **Fix:** confirm with `gh api repos/microsoft/TRELLIS.2`; if it exists, update YAML-A.
3. **`hunyuan3d_2_1` license non-SPDX.** "Tencent Hunyuan community license" has source-available restrictions — not SPDX. **Fix:** record `LicenseRef-TencentHunyuanCommunity` (SPDX `LicenseRef-` prefix is the canonical escape hatch for non-list licenses) and add a `license_url` field to YAML schema.
4. **`model_context_protocol` repo wrong.** YAML-A points at `modelcontextprotocol/specification.git` (the spec repo) but the loader expects the SDK at `modelcontextprotocol/modelcontextprotocol.git`. **Fix:** decide whether the registry tracks spec or impl; one repo per row.
5. **`enraged_rabbit_project` repo divergence.** Two completely different repos. JSON repo is the original community repo, YAML's is `ERCF_v2`. **Fix:** clarify which is canonical; both should not appear under one `id`.
6. **All 41 deprecated SPDX identifiers.** Bare `GPL-3.0`, `LGPL-3.0`, `LGPL-2.0`, `AGPL-3.0`, `GPL-2.0` were deprecated in SPDX v3.0 (Receipt #1). Fedora 41 packaging requires non-deprecated SPDX identifiers (Receipt #2). **Fix:** mass-update to `-only` or `-or-later` per upstream `LICENSE` headers.
7. **`tested_versions` absent on 60/60.** Without it, no agent can gate "is current detected_version compatible with our integration?". **Fix:** add `tested_versions: ["X.Y.Z"]` schema requirement to YAML-A; backfill from upstream release tags.
8. **YAML-B is dead schema.** The brief calls it "primary," but the loader never reads it; its richer fields (`os_support`, `version_policy`, `install`, `verify`, `adapter`) are inaccessible to runtime. **Fix:** either retire YAML-B or merge its fields into YAML-A and update `load_modules.py::_registry_path()` to load both.
9. **`pymesh` id↔repo mismatch.** YAML-A `id: pymesh` but `SOURCE_OVERRIDES` pins repo `pyvista/pymeshfix.git` → the `id` is misleading. **Fix:** rename `id` to `pymeshfix` to eliminate confusion; loader's MANIFEST_ID_ALIASES already handles `strec3d→strecs3d` precedent.
10. **9 rows with `repo_policy: verify_source_before_claiming` block all auto-update.** These rows require human verification before any update PR can merge. **Fix:** add explicit `update_status: blocked-pending-vendor-verify` enum so dashboards can render this as a state, not a hidden YAML key.

## 4. Recommended schema additions (ranked)

1. **`license_verified: bool`** — required; default `false` for any non-SPDX license or any row with `repo_policy: verify_*`. Gate update PRs on `true`.
2. **`spdx: <SPDX-id-or-LicenseRef>`** — separate canonical SPDX field; `license:` becomes free-text display only. Lets the validator hard-fail deprecated identifiers.
3. **`tested_versions: [str]`** — minimum 1 entry, format `X.Y.Z` or git short-SHA. Required for non-`research` rows.
4. **`firmware_archive_dir: str`** (firmware rows only) — explicit directory under proof/ where flashed-firmware artifacts must land for safety audit; pairs with the existing `safety:` flag.
5. **`weights_revision: str`** (gen3d rows only: `trellis`, `hunyuan3d_2_1`, `triposr`, `comfyui_trellis_wrapper`) — pin the model-weights revision distinct from the code repo SHA.
6. **`update_status: enum{stable, candidate, blocked-pending-vendor-verify, vendor-pinned, deprecated, fork-only, mirror-only}`** — replaces ad-hoc `repo_policy:` strings.
7. **`proof_redaction_required: bool`** — for proprietary/community-license rows (`flsun_slicer`, `hunyuan3d_2_1`) so proof artifacts redact vendor IP before publishing.
8. **`canonical_section: str`** — explicit normalized section key separate from the human-readable `section:` string ("Slicer / FLSUN" → `slicers`).
9. **`upstream_release_url: str`** — direct GitHub releases endpoint; lets `update_status` checks query without scraping.

## 5. Receipts

**Receipt #1 (primary, SPDX):** [SPDX License List](https://spdx.org/licenses/) — confirms `GPL-3.0`, `LGPL-3.0`, `LGPL-2.0`, `AGPL-3.0`, `GPL-2.0` (bare) are **deprecated** since SPDX v3.0; canonical replacements are `<id>-only` and `<id>-or-later`. "Tencent Hunyuan community license" and "proprietary" are NOT canonical SPDX identifiers — must use `LicenseRef-` prefix.

**Receipt #2 (cross-project Linux distro):** [Fedora Project — SPDX Licenses Phase 1](https://fedoraproject.org/wiki/Changes/SPDX_Licenses_Phase_1) and [Phase 4](https://fedoraproject.org/wiki/Changes/SPDX_Licenses_Phase_4) — Fedora 41 requires SPDX expressions in `License:` field for all RPM packages (~99.6% migrated as of early 2025). Bare deprecated identifiers fail review.

**Word count:** ~1,420 words.
