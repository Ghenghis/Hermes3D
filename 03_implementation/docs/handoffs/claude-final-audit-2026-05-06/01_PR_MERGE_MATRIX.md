# PR Merge Matrix — Hermes3D 20-Lane Wave

Generated: 2026-05-07T01:03 UTC
Base branch: `feat/hermes3d-7-complete-gui-repo-wiring`
Remote: `https://github.com/Ghenghis/Hermes3D`

All PRs target `feat/hermes3d-7-complete-gui-repo-wiring` unless noted.

---

## Pre-Merge Gate (run once before any merge)

```powershell
gh pr list --repo Ghenghis/Hermes3D --state open --json number,mergeStateStatus
```

All must show `CLEAN` before merging. PR #80 may show `UNSTABLE` while CI runs.

---

## Merge Order

### Step 0 — TS7026 Fix (merge first)

| PR | Title | Branch | Merge State | Conflict | Action |
|---|---|---|---|---|---|
| #80 | ci(fix): extend ui-ci.yml PR trigger to feat/** | claude/ts7026-ci-trigger-fix | UNSTABLE (CI running) | None | Wait for CI green, then `gh pr merge 80 --squash` |

### Tier 1 — No-Conflict PRs (merge in any order)

| PR | Title | Branch | Merge State | Audit | Conflict | Action |
|---|---|---|---|---|---|---|
| #53 | docs(roadmap): sync Hermes3D state | claude/docs-proof | CLEAN | PASS | None | Merge |
| #54 | feat(app-shell): resizable panels + Simple/Main | claude/app-shell | CLEAN | PASS | None | Merge |
| #55 | test(e2e): tab-specific Playwright specs | claude/playwright | CLEAN | PASS | None | Merge |
| #56 | test(security): MCP boundary + secret-redaction | claude/security-mcp | CLEAN | PASS | None | Merge |
| #57 | feat(source-gen3d): ComfyUI/TRELLIS/Hunyuan3D/TripoSR | claude/source-gen3d | CLEAN | PASS | None | Merge |
| #58 | feat(source-firmware): firmware gates, no-flash safety | claude/source-firmware | CLEAN | PASS | None | Merge |
| #59 | feat(source-printfarm): read-only Moonraker/Klipper | claude/source-printfarm | CLEAN | PASS | None | Merge |
| #60 | feat(source-modelers): Blender/OpenSCAD/FreeCAD | claude/source-modelers | CLEAN | PASS | None | Merge |
| #61 | feat(artifacts): proof bundle index + discovery API | claude/artifacts-proof | CLEAN | PASS | None | Merge |
| #62 | feat(learning-autopilot): truthful idle work | claude/learning-autopilot | CLEAN | PASS | None | Merge |
| #63 | feat(source-slicers): slicer CLI verifiers | claude/source-slicers | CLEAN | PASS | None | Merge |
| #65 | feat(design): CAD template gallery + provider health | claude/design | CLEAN | PASS | None | Merge |
| #67 | feat(observe): camera grid + S1 + refresh | claude/observe | CLEAN | PASS | None | Merge |
| #68 | feat(jobs): policy-gated repair/retry/rollback | claude/jobs | CLEAN | PASS | None | Merge |
| #70 | feat(gen3d): provider readiness + templates | claude/gen3d | CLEAN | PASS | None | Merge |

**Command:**
```bash
gh pr merge 53 54 55 56 57 58 59 60 61 62 63 65 67 68 70 --squash
```

### Tier 2 — App Router Sequence (`api/app.py` conflict)

| PR | Title | Branch | Merge State | Conflict File | Merge Order | Action |
|---|---|---|---|---|---|---|
| #66 | feat(source-ui): SourceOS CLI readiness panel | claude/source-ui | CLEAN | `api/app.py` (source router) | FIRST | `gh pr merge 66 --squash` |
| #69 | feat(settings-plugins): update center + rollback | claude/settings-plugins | CLEAN | `api/app.py` (settings router) | SECOND | Resolve conflict keeping BOTH routers, then merge |

**Resolution rule for #69:** `api/app.py` will have diverged. Keep all `include_router(source_os_router, ...)` lines from #66 **and** all `include_router(settings_router, ...)` lines from #69. Do not drop either.

```bash
gh pr merge 66 --squash
# then in #69's branch: git merge feat/hermes3d-7-complete-gui-repo-wiring, keep both routers
gh pr merge 69 --squash
```

### Tier 3 — Adapter Sequence (`adapters.ts` / `adapters.live.ts` conflict)

| PR | Title | Branch | Merge State | Conflict Files | Merge Order | Action |
|---|---|---|---|---|---|---|
| #64 | feat(voice): transcript + playback + proof review | claude/voice | CLEAN | `api/adapters.ts`, `api/adapters.live.ts` | FIRST | `gh pr merge 64 --squash` |
| #71 | feat(printers): onboarding wizard + S1 camera lock | claude/printers | CLEAN | `api/adapters.ts`, `api/adapters.live.ts` | SECOND | Resolve keeping ALL voice AND printer methods |

**Resolution rule for #71:** `adapters.ts` and `adapters.live.ts` will both have diverged. Keep all `voice*` adapter methods from #64 **and** all `printer*` adapter methods from #71. Do not drop either set.

```bash
gh pr merge 64 --squash
# then in #71's branch: git merge feat/hermes3d-7-complete-gui-repo-wiring, keep both method sets
gh pr merge 71 --squash
```

### Tier 4 — Final Integration Report

| PR | Title | Branch | Merge State | Conflict | Action |
|---|---|---|---|---|---|
| #72 | docs(integration): 20-agent completion report | claude/final-integrator | CLEAN | None | Merge last after Tiers 1–3 |

```bash
gh pr merge 72 --squash
```

### Audit PRs (docs/proof only — no code conflicts)

| PR | Title | Branch | Audit # | Verdict | Action |
|---|---|---|---|---|---|
| #74 | audit(runtime): source OS + verifier + route truth | claude/polish-runtime-audit | 3 | PASS | Merge |
| #75 | audit(merge): merge integrity verification | claude/polish-merge-audit | 1 | PASS | Merge |
| #76 | audit(security): secret + traversal + shell | claude/polish-security-audit | 5 | PASS | Merge |
| #77 | audit(safety): printer/camera/physical safety | claude/polish-safety-audit | 4 | PASS | Merge |
| #78 | audit(docs): PR bodies + ROADMAP + merge plan | claude/polish-docs-audit | 6 | PASS (low/med doc gaps) | Merge |
| #79 | audit(nofake-ui): 0 violations — button wiring | claude/polish-nofake-audit | 2 | PASS | Merge |

```bash
gh pr merge 74 75 76 77 78 79 --squash
```

### Codex-Owned PR (not in Claude merge sequence)

| PR | Title | Branch | State | Action |
|---|---|---|---|---|
| #73 | [codex] add MCP-locked Hermes Agent code operator | codex/hermes-agent-mcp-code-operator | DRAFT, CLEAN | Codex merges when code-operator is complete |

---

## Conflict-Prone Files (reference)

| File | Conflicting PRs | Resolution |
|---|---|---|
| `03_implementation/src/hermes3d/api/app.py` | #66, #69 | Keep both routers; union all `include_router` calls |
| `03_implementation/ui/src/api/adapters.ts` | #64, #71 | Keep all voice methods AND all printer methods |
| `03_implementation/ui/src/api/adapters.live.ts` | #64, #71 | Same — keep all method implementations from both |

---

## Post-Merge Global Gates

Run after all Tier 1–4 lane PRs are merged:

```powershell
cd 03_implementation/ui
npm install
npm run lint        # must show 0 errors after node_modules present
npm run build       # vite tsc -b + bundle

cd ..
python -m py_compile src/hermes3d/api/routes/*.py src/hermes3d/services/*.py
python scripts/scan_active_ui_no_fake.py   # must show 0 violations
```
