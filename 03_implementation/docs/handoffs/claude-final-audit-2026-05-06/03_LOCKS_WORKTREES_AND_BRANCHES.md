# Locks, Worktrees, and Branches

Generated: 2026-05-07T01:03 UTC
Hermes workspace: `G:\Github\Hermes3D`
Lock count at snapshot: 84 active (0 stale)

---

## Hermes Lock State Before Release

Total: **84 active locks** across 6 Claude agent owners + codex-master.

### Claude-Owned Locks (to be released by this handoff)

#### claude-source-gen3d-04 (8 files)
| File | Task |
|---|---|
| `03_implementation/adapter_registry/schemas/bambustudio_bridge.schema.json` | a2a_1778106411818_946d5ec0 |
| `03_implementation/adapter_registry/schemas/comfyui.schema.json` | a2a_1778106411818_946d5ec0 |
| `03_implementation/adapter_registry/schemas/hunyuan3d.schema.json` | a2a_1778106411818_946d5ec0 |
| `03_implementation/adapter_registry/schemas/trellis2.schema.json` | a2a_1778106411818_946d5ec0 |
| `03_implementation/adapter_registry/schemas/triposr.schema.json` | a2a_1778106411818_946d5ec0 |
| `03_implementation/proof/GEN3D_VERIFY_2026-05-06.json` | a2a_1778106411818_946d5ec0 |
| `03_implementation/scripts/verify_gen3d.py` | a2a_1778106411818_946d5ec0 |
| `03_implementation/tests/source_lab/test_gen3d.py` | a2a_1778106411818_946d5ec0 |

#### claude-source-printfarm-03 (4 files)
| File | Task |
|---|---|
| `03_implementation/adapter_registry/schemas/fdm_monster.schema.json` | a2a_1778106404784_388da127 |
| `03_implementation/adapter_registry/schemas/fluidd.schema.json` | a2a_1778106404784_388da127 |
| `03_implementation/adapter_registry/schemas/klipperscreen.schema.json` | a2a_1778106404784_388da127 |
| `03_implementation/adapter_registry/schemas/mainsail.schema.json` | a2a_1778106404784_388da127 |

#### claude-polish-nofake-02 (1 file)
| File | Task |
|---|---|
| `03_implementation/docs/handoffs/audit/NOFAKE_UI_2026-05-06.md` | H3D-CLAUDE-POLISH-NOFAKE-UI-2026-05-06 |

#### claude-design-12 (6 files)
| File | Task |
|---|---|
| `03_implementation/proof/DESIGN_TEMPLATES_2026-05-06.json` | a2a_1778106609412_5c54a4fb |
| `03_implementation/templates/design/desk_organizer.json` | a2a_1778106609412_5c54a4fb |
| `03_implementation/templates/design/parametric_box.json` | a2a_1778106609412_5c54a4fb |
| `03_implementation/ui/src/types/design.ts` | a2a_1778106609412_5c54a4fb |
| `03_implementation/ui/tests/e2e/design.detail.spec.ts` | a2a_1778106609412_5c54a4fb |
| `04_testing/pytest/test_design_routes.py` | a2a_1778106609412_5c54a4fb |

#### claude-gen3d-13 (8 files)
| File | Task |
|---|---|
| `03_implementation/proof/GEN3D_PROVIDER_READINESS_2026-05-06.json` | (gen3d lane task) |
| `03_implementation/templates/gen3d/calibration_cube.json` | (gen3d lane task) |
| `03_implementation/templates/gen3d/spool_holder.json` | (gen3d lane task) |
| `03_implementation/tests/api/test_generation_routes.py` | (gen3d lane task) |
| `03_implementation/ui/src/components/gen3d/GenerationStatus.tsx` | (gen3d lane task) |
| `03_implementation/ui/src/components/gen3d/ProviderList.tsx` | (gen3d lane task) |
| `03_implementation/ui/src/components/gen3d/TemplatePicker.tsx` | (gen3d lane task) |
| `03_implementation/ui/src/types/generation.ts` | (gen3d lane task) |

#### claude-source-modelers-02 (1 file)
| File | Task |
|---|---|
| `03_implementation/proof/MODELER_VERIFY_2026-05-06.json` | a2a_1778106377800_aefa0bbb |

**Total Claude-owned locks to release: 28**

### Codex-Master Locks (do NOT release — active in-flight work)

42 files locked by `codex-master` covering:
- Backend routes: `api/app.py`, `api/routes/modules.py`, `api/routes/settings.py`, `api/routes/agent_updates.py`, `api/routes/desktop_compat.py`, `api/routes/desktop_updates.py`, `api/routes/roadmap.py`
- Services: `core/orchestration/print_workflow.py`, `core/printers/moonraker_client.py`, `core/slicer/*.py`, `services/local_state.py`
- DB: `db/init.py`, `db/load_modules.py`, `db/schema.sql`
- UI shell: `App.tsx`, `AppShell.tsx`, `store.ts`, `Sidebar.tsx`, `TopBar.tsx`, `Panel.tsx`, `globals.css`, `tailwind.config.ts`
- UI tabs: `Agents.tsx`, `Dashboard.tsx`, `Plugins.tsx`, `Roadmap.tsx`
- UI types: `job-detail.ts`, `learning.ts`, `printer.ts`, `proof.ts`, `roadmap.ts`, `source-os.ts`, `system.ts`
- Proof/scripts: `ACTIVE_UI_NO_FAKE_SWEEP.md`, `LOCAL_TOOLING_AUDIT.json`, `FLSUN_PROFILE_SOURCE_AUDIT.json`, `audit_local_tooling.py`, `extract_flsun_profile_sources.py`, `scan_active_ui_no_fake.py`
- Config: `config/printers.toml`

**These codex-master locks represent active code-operator work (PR #73). Codex releases them when the code-operator feature is complete.**

---

## Hermes Lock State After Claude Release

After this handoff runs `hermes_release_files` for all 28 Claude-owned files:
- Remaining active locks: **56** (all owned by codex-master)
- Claude-owned locks: **0**

---

## Claude Worktrees

All Claude worktrees are in `G:/Github/_claude_worktrees/`:

| Worktree | Branch | PR | Status |
|---|---|---|---|
| h3d-claude-app-shell | claude/app-shell | #54 | PR open, CLEAN |
| h3d-claude-artifacts-proof | claude/artifacts-proof | #61 | PR open, CLEAN |
| h3d-claude-design | claude/design | #65 | PR open, CLEAN |
| h3d-claude-docs-proof | claude/docs-proof | #53 | PR open, CLEAN |
| h3d-claude-final-integrator | claude/final-integrator | #72 | PR open, CLEAN |
| h3d-claude-gen3d | claude/gen3d | #70 | PR open, CLEAN |
| h3d-claude-jobs | claude/jobs | #68 | PR open, CLEAN |
| h3d-claude-learning-autopilot | claude/learning-autopilot | #62 | PR open, CLEAN |
| h3d-claude-observe | claude/observe | #67 | PR open, CLEAN |
| h3d-claude-playwright | claude/playwright | #55 | PR open, CLEAN |
| h3d-claude-printers | claude/printers | #71 | PR open, CLEAN |
| h3d-claude-security-mcp | claude/security-mcp | #56 | PR open, CLEAN |
| h3d-claude-settings-plugins | claude/settings-plugins | #69 | PR open, CLEAN |
| h3d-claude-source-firmware | claude/source-firmware | #58 | PR open, CLEAN |
| h3d-claude-source-gen3d | claude/source-gen3d | #57 | PR open, CLEAN |
| h3d-claude-source-modelers | claude/source-modelers | #60 | PR open, CLEAN |
| h3d-claude-source-printfarm | claude/source-printfarm | #59 | PR open, CLEAN |
| h3d-claude-source-slicers | claude/source-slicers | #63 | PR open, CLEAN |
| h3d-claude-source-ui | claude/source-ui | #66 | PR open, CLEAN |
| h3d-claude-voice | claude/voice | #64 | PR open, CLEAN |
| h3d-polish-docs | claude/polish-docs-audit | #78 | PR open, CLEAN |
| h3d-polish-merge | claude/polish-merge-audit | #75 | PR open, CLEAN |
| h3d-polish-nofake | claude/polish-nofake-audit | #79 | PR open, CLEAN |
| h3d-polish-runtime | claude/polish-runtime-audit | #74 | PR open, CLEAN |
| h3d-polish-safety | claude/polish-safety-audit | #77 | PR open, CLEAN |
| h3d-polish-security | claude/polish-security-audit | #76 | PR open, CLEAN |
| h3d-ts7026-fix | claude/ts7026-ci-trigger-fix | #80 | PR open, UNSTABLE (CI) |
| **h3d-final-handoff** | **claude/final-codex-handoff** | **(this PR)** | **active** |

**Do not delete worktrees until their PR is merged.** After merge, Codex may prune with:
```bash
git worktree remove --force G:/Github/_claude_worktrees/h3d-claude-<name>
```

---

## Active A2A Tasks at Handoff Time

| Task ID | Agent | Type | Status | PR |
|---|---|---|---|---|
| a2a_1778115796454_685e7b14 | claude-orchestrator | final_handoff_bundle | claimed (active) | this PR |
| a2a_1778114702912_1ac758ea | claude-orchestrator | ts7026_fix_pr | submitted (done) | #80 |
| a2a_1778109984162_cf2af3d6 | claude-voice-09 | implementation | submitted (done) | #64 |
| a2a_1778106609412_5c54a4fb | claude-design-12 | design_tab_wire | working (done) | #65 |
| a2a_1778106463518_96bc875c | claude-source-firmware-05 | source_firmware_verify | submitted (done) | #58 |
| a2a_1778106411818_946d5ec0 | claude-source-gen3d-04 | source_gen3d_verify | working (done) | #57 |
| a2a_1778106404784_388da127 | claude-source-printfarm-03 | source_printfarm_verify | working (done) | #59 |
| a2a_1778106377800_aefa0bbb | claude-source-modelers-02 | source_modelers_verify | working (done) | #60 |
| a2a_1778106191786_15f6e737 | claude-orchestrator | coordination | submitted (done) | — |

All tasks with status `submitted` or `working` are completed (PRs open). Hermes auto-archives after 24h.
