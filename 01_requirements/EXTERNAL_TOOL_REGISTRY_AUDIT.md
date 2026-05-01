# External Tool Registry Audit — Phase 0

> **Status:** Phase 0 audit. Reference: `hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml` (the registry) + `hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py` (the validator).

This document captures the Phase 0 state of the external tool registry, what its validator can and cannot enforce today, and the work items Phase 1 must pick up.

## 1. Coverage matrix — locked tools

The user has locked 10 integration targets (each must be supportable in BOTH "docked inside Hermes3D UI" AND "launched as a full external app" modes). All 10 are present in the registry. The registry also includes Cura (extra, optional) and a second Blender MCP provider (`blender_mcp_vxai`, optional/experimental) — both are reasonable surplus, not violations.

| # | Locked tool | Registry key | Adapter mode | Dock | External launch | License | Version pin |
|---|---|---|---|---|---|---|---|
| 1 | Blender | `blender` | `external_process` | `dock_if_supported` | `launch_external` | **not captured** | `channel: stable` + `manual_select` |
| 2 | Blender MCP | `blender_mcp_ahujasid` (+ optional `blender_mcp_vxai`) | `mcp` | n/a (provider) | n/a | **not captured** | `channel: stable / experimental` + `manual_select` |
| 3 | FLSunSlicer | `flsun_slicer` | `external_process` | **NOT declared** | `launch_external` | **not captured** | `channel: user_provided_or_stable` + `manual_select` |
| 4 | PrusaSlicer | `prusa_slicer` | `cli_external_process` | **NOT declared** | `launch_external` | **not captured** (GPL/AGPL upstream) | `channel: stable` + `manual_select` |
| 5 | OrcaSlicer | `orca_slicer` | `cli_external_process` | **NOT declared** | `launch_external` | **not captured** (GPL upstream) | `channel: stable` + `manual_select` |
| 6 | Printrun | `printrun` | `cli_or_gui_external_process` | **NOT declared** | `launch_external` | **not captured** (GPL upstream) | `channel: stable` + `manual_select` |
| 7 | Moonraker | `moonraker` | `http_api` | n/a (headless API) | n/a | **not captured** | `channel: existing_printer_service` + `manual_select` |
| 8 | Fluidd | `fluidd` | `web_embed_or_external` | `dock_if_allowed` | `fullscreen_external` | **not captured** | `channel: existing_printer_ui` + `manual_select` |
| 9 | Mainsail | `mainsail` | `web_embed_or_external` | `dock_if_allowed` | `fullscreen_external` | **not captured** | `channel: existing_printer_ui` + `manual_select` |
| 10 | OctoPrint | `octoprint` | `http_api_and_web_embed` | `dock_if_allowed` | (web embed implicit; **`fullscreen_external` token absent**) | **not captured** | `channel: existing_service_or_stable` + `manual_select` |

**Coverage: 10/10 locked. Surplus: 2 (Cura provisioning + experimental MCP provider).**

## 2. Validator run

```
$ python hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py \
       hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml
Registry validation PASS: 12 tools checked
$ echo $?
0
```

The default-path invocation (no path argument) silently fails with `ERROR: registry not found: config\external_repos_registry.yaml` because the script's default is CWD-relative. From the repo root, the path argument is mandatory. **Phase 1 must anchor the default to the script's own location.**

## 3. Schema — what's enforced today

`validate_registry.py` requires per tool:
- `name`, `type`, `required`, `version_policy`, `install`, `verify`, `adapter`, `os_support`
- At least one of `repo` / `source` / `homepage`
- `install.method`, `verify.commands`, `verify.expected`, `adapter.mode`, `adapter.capabilities`
- `version_policy` containing one of `pin | channel | manual_select | locked`

**Schema enforcement gaps (NOT validated today):**
- `license` — no entry declares it. Half the locked list is GPL/AGPL upstream.
- Per-`type` capability matrix — slicers and Printrun lack any `dock_*` token despite the user requirement.
- Semantic version pins — `pin` and `locked` are listed as alternatives but every entry uses `manual_select: true`.
- URL shape sanity — a malformed `repo: ""` or typo'd URL would pass silently.
- Reproducibility — no `tested_versions` list per entry.

## 4. Pseudocode vs real validator — STALE

The kit ships TWO files that look like validators:
- `hermes3d_gui_contract_kit_v4.1/scripts/registry_validator_pseudocode.py` — pseudocode
- `hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py` — real validator

They are in serious schema drift:

| Aspect | pseudocode | real validator |
|---|---|---|
| Top-level YAML key | `repositories` | `tools` (with fallback) |
| Required fields | `display_name`, `role`, `adapter` | `name`, `type`, `required`, `version_policy`, `install`, `verify`, `adapter`, `os_support` |
| URL alternatives | `repo_url` or `local_user_archives` | `repo` or `source` or `homepage` |
| Sub-key validation | none | `install.method`, `verify.commands/expected`, `adapter.mode/capabilities`, `version_policy` shape |

The actual registry uses `tools:` and `name:` / `repo:` — i.e. the **real validator's** vocabulary, not the pseudocode's. The pseudocode would falsely report "No repositories declared" against the live registry. **Phase 1 must either delete the pseudocode or regenerate it from the real validator before Phase 1 implementers reference it.**

## 5. Findings

| # | Severity | Finding |
|---|---|---|
| 1 | **HIGH** | `registry_validator_pseudocode.py` is stale — describes a different schema than the live registry. Misleading reference. Delete or regenerate before Phase 1 reads it. |
| 2 | MED | No `license` field on any entry. Compliance audit and bundle gating will need this; required at least for slicers (PrusaSlicer / OrcaSlicer / Printrun / Cura — all GPL) and printer services (OctoPrint / Moonraker). |
| 3 | MED | Slicers (`prusa_slicer`, `orca_slicer`, `flsun_slicer`, `cura`) and `printrun` declare no `dock_*` capability token. The user's locked requirement is "BOTH docked AND external" for every locked tool. Either the requirement applies only to UI-bearing tools (in which case document that exception), or these entries are missing the dock token. |
| 4 | MED | Validator does not enforce per-`type` capability requirements. A future entry could declare `adapter.capabilities: []` and pass. Phase 1 should add a per-type matrix (e.g. `slicer` MUST have `cli` + `external`-launch, `printer-ui` MUST have `dock_iframe` + `fullscreen_external`). |
| 5 | LOW | All 12 entries use `manual_select: true`. For reproducible bundles, every entry should declare a `tested_versions` list even when install-time selection remains manual. |
| 6 | LOW | URL drift between `install_plan.md` line 21 (`OrcaSlicer/OrcaSlicer`) and the registry (`SoftFever/OrcaSlicer`). The registry is correct (SoftFever is canonical). The install-plan instructions would 404. |
| 7 | LOW | Validator does not URL-shape-check `repo` / `source` / `homepage`. An empty string or typo'd URL passes silently. |
| 8 | LOW | Validator's default registry path is CWD-relative (silently fails from repo root). Anchor to script location instead. |
| 9 | LOW | `octoprint` adapter capabilities omit a `fullscreen_external` token that other web-UI entries (`fluidd`, `mainsail`) carry. Vocabulary inconsistency across web-embed entries. |
| 10 | INFO | `blender_mcp_vxai` is `required: false` and `experimental` — fine. Bumps the validator count to 12 vs the locked list of 10. Not a violation. |

## 6. Phase 1 work items — registry validator implementation

In order of urgency:

1. **Replace or regenerate `registry_validator_pseudocode.py`** so implementers can't follow the wrong schema by accident.
2. **Add a `license` field** to the required schema with SPDX-string validation (`GPL-3.0-or-later`, `AGPL-3.0-or-later`, `Apache-2.0`, `MIT`, `proprietary`, etc.).
3. **Add per-`type` capability matrix.** Sketch:
   - `slicer` MUST declare `cli` + a dock-capable token (`dock_if_allowed` or `dock_if_supported`) + `launch_external`.
   - `external_app` MUST declare `dock_if_supported` + `launch_external`.
   - `external_web_ui` MUST declare `dock_if_allowed` + `fullscreen_external`.
   - `printer_api` / `mcp_provider` are exempt from dock requirements.
   - `printer_control_usb` MUST declare a dock token + `launch_external`.
4. **Add `tested_versions`** list per entry (even when install is `manual_select`, record what was last verified).
5. **Strengthen URL validation** — regex `^https?://`, reject empty strings, sanity-check the host.
6. **Add a structured error model** — return `(tool_id, level, code, message)` tuples so a CI gate can consume the output programmatically.
7. **Anchor the default registry path** to the script location: `Path(__file__).parent.parent / "config" / "external_repos_registry.yaml"`.
8. **Fix the `install_plan.md` OrcaSlicer URL** (or auto-generate the install plan from the registry — single source of truth).
9. **Optional improvement:** add an explicit `dock_modes` object per entry — `{dock: bool, external: bool, headless: bool}` — to make the user's "BOTH docked and external" requirement testable directly rather than inferred from capability tokens.
10. **Enforce single-required-MCP-provider rule:** exactly one Blender MCP provider may have `required: true` per upstream tool.

## 7. Phase 0 verdict

**AMBER** — registry has full coverage of the locked list and passes its own schema check. The findings above are real and worth fixing before Phase 1 ships its validator, but **none block Phase 1 from starting** — they ARE the Phase 1 work.

**Phase 1 readiness for the registry axis: GO.** Start with finding #1 (stale pseudocode) so implementers are reading the correct schema from day one.

## 8. Cross-links

- Live registry: [`config/external_repos_registry.yaml`](../hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml)
- Validator: [`scripts/validate_registry.py`](../hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py)
- Stale pseudocode (to be reconciled): [`scripts/registry_validator_pseudocode.py`](../hermes3d_gui_contract_kit_v4.1/scripts/registry_validator_pseudocode.py)
- Repo policy: [`01_requirements/REPO_POLICY.md`](../hermes3d_gui_contract_kit_v4.1/01_requirements/REPO_POLICY.md)
- Tool integration requirements: [`01_requirements/TOOL_INTEGRATION_REQUIREMENTS.md`](../hermes3d_gui_contract_kit_v4.1/01_requirements/TOOL_INTEGRATION_REQUIREMENTS.md)
- Install plan: [`scripts/install_plan.md`](../hermes3d_gui_contract_kit_v4.1/scripts/install_plan.md)
- Tool install verification: [`04_testing/integration/TOOL_INSTALL_VERIFICATION_COMMANDS.md`](../hermes3d_gui_contract_kit_v4.1/04_testing/integration/TOOL_INSTALL_VERIFICATION_COMMANDS.md)
- Phase 0 adapter registry: [`03_implementation/adapter_registry/README.md`](../03_implementation/adapter_registry/README.md)
- Phase 0 baseline report: [`00_overview/PHASE0_BASELINE_REPORT.md`](../00_overview/PHASE0_BASELINE_REPORT.md)
