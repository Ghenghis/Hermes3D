# Open Blockers and Fix Queue

Generated: 2026-05-07T01:03 UTC
Source: 6-agent strict audit pass (PRs #74–#79)

---

## Summary

| Severity | Count | All code-blocking? |
|---|---|---|
| HIGH (code, blocks merge) | 0 | — |
| MEDIUM (fix before release) | 1 | No (TS7026 CI fix PR open) |
| LOW (polish, non-blocking) | 4 | No |
| INFO (acknowledged gaps) | 3 | No |

**Zero blockers prevent merging the 20 lane PRs.**

---

## MEDIUM — Fix In Progress

### M1: TS7026/TS7006 JSX.IntrinsicElements type regression absent from CI gate

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Owner | claude-orchestrator (fix open), Codex (merge) |
| PR | #80 `claude/ts7026-ci-trigger-fix` |
| File | `.github/workflows/ui-ci.yml` |
| Proof | `npm run lint` returns 0 errors AFTER `npm install`; tsconfig.json `"jsx": "react-jsx"` and `@types/react: 18.3.11` are correct |
| Root cause | `git worktree add` creates worktrees without `node_modules`. `ui-ci.yml` `pull_request.branches` only listed `[main, develop]` — lane PRs targeting `feat/hermes3d-7-complete-gui-repo-wiring` never triggered CI lint |
| Fix | Add `"feat/**"` to `pull_request.branches` list in `ui-ci.yml`. Committed in PR #80 |
| Status | PR #80 UNSTABLE (CI running). Expected to pass when runner completes `npm ci` |
| Codex action | Wait for #80 CI green → `gh pr merge 80 --squash`. Merge before Tier 1 lanes so coverage applies |

---

## LOW — Doc/PR Body Gaps (non-blocking, polish only)

### L1: PR #53 body is prose-only — no structured table

| Field | Value |
|---|---|
| Severity | LOW |
| Owner | Codex (optional polish) |
| PR | #53 `claude/docs-proof` |
| Finding | PR body lists changed files as plain prose rather than the structured table format used by other lane PRs |
| Impact | No code or functional impact. Makes review slightly harder |
| Proof | Audit 6 (PR #78) finding |
| Codex action | Accept as-is, or edit PR #53 body to add a files table before merging |

### L2: PR #64 body format non-standard

| Field | Value |
|---|---|
| Severity | LOW |
| Owner | Codex (optional polish) |
| PR | #64 `claude/voice` |
| Finding | PR body format diverges from the canonical lane PR template (missing explicit "Changed files" section) |
| Impact | No code or functional impact |
| Proof | Audit 6 (PR #78) finding |
| Codex action | Accept as-is, or normalize before merging |

### L3: README feature count may be stale

| Field | Value |
|---|---|
| Severity | LOW |
| Owner | Codex |
| File | `README.md` (root) |
| Finding | Audit 6 noted README may overclaim or underclaim completed UI tabs |
| Impact | No runtime impact. Documentation accuracy only |
| Codex action | After all 20 lane PRs merge: update README to list all completed tabs and current feature count |

### L4: ROADMAP TS7026 gap entry (if not already added)

| Field | Value |
|---|---|
| Severity | LOW |
| Owner | Codex |
| File | `03_implementation/ROADMAP.md` |
| Finding | The pre-existing TS7026 regression may not have a concrete next-action entry in ROADMAP |
| Proof | PR #80 fixes the CI trigger; no ROADMAP entry observed by Audit 6 |
| Codex action | After PR #80 merges, add a ROADMAP entry confirming the CI gate is restored. If already present, no action |

---

## INFO — Acknowledged Gaps (not assigned for fix)

### I1: Source OS runtime UNKNOWN badges

Some Source OS apps show `UNKNOWN` runtime status badges because their toolchain is not installed on the CI runner (ComfyUI, TRELLIS, Hunyuan3D). These are **correct** — Audit 3 verified that `UNKNOWN` badges are caused by genuinely missing runtimes, not missing implementation.

**Codex action:** Document each gap in ROADMAP with a concrete next action (install hook or skip condition). No code change required to unblock merges.

### I2: codex-master Hermes locks on core files

42 files are locked by `codex-master` covering core backend (api routes, UI shell components, schema, services). These locks represent active codex-master work on PR #73. Do not release them — they will auto-expire or be manually released by codex-master.

**Codex action:** None. Normal in-flight codex work.

### I3: Stale A2A task status (sub-agent tasks show "working"/"submitted")

Several A2A tasks from completed sub-agents remain in `working` or `submitted` status (Hermes auto-archives tasks after 24h). This is a cosmetic state issue — the actual PRs are open and CI-CLEAN.

**Codex action:** Tasks will auto-archive after 24h. No manual action needed.
