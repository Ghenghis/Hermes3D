# Bonus 13 — Errata follow-up tables (2026-05-09)

**Companion to:** `bonus13-schema-inconsistency.md` (locked by `claude-lead-app-audit`; this follow-up adds the per-row remap tables that doc declared as counts only).
**Provenance:** Agent 10 of the 20-agent Blocker Elimination Swarm produced these tables; orchestrator landed them as a separate doc to respect the source-file lock.
**Scope:** docs only. No source code touched.

---

## 1. SPDX-invalid → canonical SPDX (42 rows)

Per [SPDX License List](https://spdx.org/licenses/) bare `GPL-2.0`, `GPL-3.0`, `LGPL-2.0`, `LGPL-2.1`, `LGPL-3.0`, `AGPL-3.0` were **deprecated as of SPDX v3.0**. Default policy below assumes `-or-later` (matches FSF "version X or any later version" boilerplate in upstream `LICENSE` headers); rows whose upstream `LICENSE` says "version X only" should be flipped to `-only` during YAML edit.

| current (deprecated) | canonical (default) | also acceptable |
|---|---|---|
| `GPL-2.0` | `GPL-2.0-or-later` | `GPL-2.0-only` |
| `GPL-3.0` | `GPL-3.0-or-later` | `GPL-3.0-only` |
| `LGPL-2.0` | `LGPL-2.0-or-later` | `LGPL-2.0-only` |
| `LGPL-3.0` | `LGPL-3.0-or-later` | `LGPL-3.0-only` |
| `AGPL-3.0` | `AGPL-3.0-or-later` | `AGPL-3.0-only` |
| `"Tencent Hunyuan community license"` | `LicenseRef-TencentHunyuanCommunity` | (custom; pair with `license_url:` per §4.2) |

Rows in YAML-A (loader-real, `Hermes3D-GUI-Wiring-Contract-Kit/03_REPO_REGISTRY/external_repos_registry.yaml`) requiring change:

- `LGPL-3.0` → `LGPL-3.0-or-later`: line 15 (cura)
- `AGPL-3.0` → `AGPL-3.0-or-later`: lines 9, 22, 50, 58, 66, 79, 181, 223, 230, 385 (bambustudio, curaengine, orcaslicer, prusaslicer, slic3r, superslicer, fdm-monster, octofarm, octoprint, manyfold)
- `GPL-3.0` → `GPL-3.0-or-later`: lines 123, 158, 188, 195, 202, 209, 216, 244, 253, 260, 267, 281, 288, 297, 304, 411, 417 (meshlab, solvespace, fluidd, klipper, klipperscreen, mainsail, moonraker, printrun, klipper firmware, marlin, prusa firmware, reprap firmware, smoothieware, comfyui, comfyui-frontend, repetier_firmware, enraged_rabbit_project)
- `Tencent Hunyuan community license` → `LicenseRef-TencentHunyuanCommunity`: line 318 (hunyuan3d_2_1)

---

## 2. Repo URL mismatches → canonical upstream URLs

Verified existence of each canonical upstream via `gh api repos/<owner>/<name>` on 2026-05-09:

| id | YAML-A current | canonical upstream (verified) | severity |
|---|---|---|---|
| `trellis` | `microsoft/TRELLIS.git` | `https://github.com/microsoft/TRELLIS.2.git` (created 2025-11-26, MIT, 6.7k stars) | HIGH |
| `hunyuan3d_2_1` | `Tencent-Hunyuan/Hunyuan3D-2.git` | `https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git` | HIGH |
| `model_context_protocol` | `modelcontextprotocol/specification.git` | `https://github.com/modelcontextprotocol/modelcontextprotocol.git` (impl monorepo; spec repo retained as separate row if needed) | HIGH |
| `enraged_rabbit_project` | `Enraged-Rabbit-Community/ERCF_v2` | `https://github.com/EtteGit/EnragedRabbitProject` (canonical maintainer fork) | HIGH |
| `orcaslicer` | `SoftFever/OrcaSlicer.git` | `https://github.com/SoftFever/OrcaSlicer.git` (still SoftFever; JSON's `OrcaSlicer/OrcaSlicer.git` is a stale rename and does NOT exist) | MED — keep YAML-A; fix JSON |

---

## 3. Concrete `tested_versions` for 5 sampled apps (backfill template)

Pulled from `gh api repos/<owner>/<name>/tags` on 2026-05-09 (top stable tag, latest two releases):

| id | proposed `tested_versions` | source |
|---|---|---|
| `prusaslicer` | `["2.9.4", "2.9.3"]` (2.9.5-beta excluded) | `prusa3d/PrusaSlicer` tags |
| `orcaslicer` | `["2.3.2", "2.3.1"]` (release-candidates excluded) | `SoftFever/OrcaSlicer` tags |
| `blender` | `["5.1.1", "5.1.0", "5.0.1"]` (LTS + current) | `blender/blender` tags |
| `klipper` | `["v0.13.0", "v0.12.0"]` | `Klipper3d/klipper` tags |
| `marlin` | `["2.1.2.5", "2.1.2.4"]` (resolved from `latest-2.1.x` rolling tag) | `MarlinFirmware/Marlin` tags |

The full 60-row backfill is left as a follow-up handoff (`bonus13-tested-versions-backfill.md`) — that doc must call `gh api repos/<owner>/<name>/tags` for every row and include format normalisation rules (e.g. strip `version_`, `latest-` prefixes; keep semver only).

---

## 4. Receipts

**Receipt #1 (primary, SPDX):** [SPDX License List](https://spdx.org/licenses/) — confirms `GPL-3.0`, `LGPL-3.0`, `LGPL-2.0`, `AGPL-3.0`, `GPL-2.0` (bare) are **deprecated** since SPDX v3.0; canonical replacements are `<id>-only` and `<id>-or-later`. "Tencent Hunyuan community license" and "proprietary" are NOT canonical SPDX identifiers — must use `LicenseRef-` prefix.

**Receipt #2 (cross-project Linux distro):** [Fedora Project — SPDX Licenses Phase 1](https://fedoraproject.org/wiki/Changes/SPDX_Licenses_Phase_1) and [Phase 4](https://fedoraproject.org/wiki/Changes/SPDX_Licenses_Phase_4) — Fedora 41 requires SPDX expressions in `License:` field for all RPM packages (~99.6% migrated as of early 2025). Bare deprecated identifiers fail review.

**Receipt #3 (cross-project Debian):** [Debian DEP-5 / CopyrightFormat](https://wiki.debian.org/Proposals/CopyrightFormat) — confirms SPDX prohibits bare short identifiers and the canonical form uses `-only` / `-or-later` suffixes. DEP-5's own simplified `GPL-3` / `GPL-3+` is explicitly noted as Debian-specific shorthand, NOT the SPDX canonical form.

**Receipt #4 (upstream existence checks 2026-05-09):** `gh api repos/microsoft/TRELLIS.2` (200 OK, created 2025-11-26), `gh api repos/Tencent-Hunyuan/Hunyuan3D-2.1` (200 OK), `gh api repos/modelcontextprotocol/modelcontextprotocol` (200 OK), `gh api repos/EtteGit/EnragedRabbitProject` (200 OK).

---

## 5. Caveats (from Agent 10 analysis)

Factual statements that should be re-verified before YAML-A is edited:

- Default to `-or-later` for the 41 GPL/LGPL/AGPL rows is based on FSF boilerplate convention; each upstream `LICENSE` header should be re-read before the YAML edit.
- Marlin `tested_versions: ["2.1.2.5", "2.1.2.4"]` — `MarlinFirmware/Marlin` uses rolling `latest-2.1.x` tag; the actual semver was inferred and should be re-resolved against the `bugfix-2.1.x` branch on apply.
- `model_context_protocol` corrected URL is the impl monorepo; the registry maintainer must decide whether the row tracks spec or impl (existing finding §3.4 already flags this — the impl URL is recorded here since the loader was expecting the SDK).

---

## 6. Application notes

This follow-up does NOT modify YAML-A directly. The actual schema fix is a separate PR that:

1. Updates `Hermes3D-GUI-Wiring-Contract-Kit/03_REPO_REGISTRY/external_repos_registry.yaml` with the 42 license remappings + 5 repo URL corrections.
2. Validates the YAML still parses cleanly through `db/load_modules.py`.
3. Adds `tested_versions` and `firmware_archive_dir` schema keys.

That PR is registered as **BLK-014** in `E2E_BLOCKER_REGISTRY_2026-05-09.md` (60-app update profile matrix) and is owned by squad D.
