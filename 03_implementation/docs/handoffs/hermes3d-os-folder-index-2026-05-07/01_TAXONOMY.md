# Taxonomy — How Folders Were Classified

Generated: 2026-05-07

This document describes the rules the orchestrator used to (a) decide which folders count as "Hermes3D OS" and (b) assign each included folder to one of the 12 categories.

---

## Inclusion Rule

A folder under `G:\Github\` is included if **all** of these hold:

1. Its `LastWriteTime` falls between **2026-04-27** and **2026-05-07** inclusive.
2. It contains code, docs, or evidence that directly supports Hermes3D OS, the Hermes Agent, the Hermes Protocol, or HermesProof.
3. It is not a vendored copy of an unrelated upstream project (exception: `apps/` slicers/modelers — these are explicitly used by Source OS and so are included).

If any test fails, the folder is excluded. See `02_EXCLUSIONS.md` for the excluded list.

---

## Category Assignment Rules

### 1. `core-repos/` — primary Hermes3D OS repos

**Match**: top-level repo or umbrella whose primary purpose is to host Hermes3D OS source/docs.

**Members** (5):
- `Hermes3D` — canonical FastAPI + MCP repo
- `h3d-gui-wiring-codex` — sibling clone for the 20-agent contract
- `Hermes3D-OS` — independent SPA + bridge repo
- `Hermes3D-worktrees` — umbrella dir for related worktrees
- `Hermes3D-handoffs` — pinned worktree for architect-brief snapshot

### 2. `agent-infra/` — Hermes Agent and MCP infrastructure

**Match**: code that implements the Hermes Agent runtime, MCP server, or coordination plane.

**Members** (5):
- `hermes-agent-fresh` — vendored NousResearch hermes-agent
- `atomic-hermes` — AtomicBot-ai macOS Electron fork
- `hermes3d-mcp-lock-orchestrator` — active orchestrator (HermesProof v0.7)
- `hermes3d-mcp-test-sandbox` — smoke-test fixture
- `hp-hermes-agent-bridge` — predecessor v0.6.0 bridge

> **Cross-reference**: `hp-hermes-agent-bridge` also matches the `hp-protocol/` rule below by prefix. It is placed in `agent-infra/` because its primary role is the active agent bridge runtime, not P0/P1 hardening sweep work. The `hp-protocol/` README explicitly notes the cross-reference.

### 3. `hp-protocol/` — Hermes Protocol P0/P1 hardening sweep

**Match**: folder name starts with `hp-` AND represents a P0/P1 priority task or audit cycle of HermesProof v0.5/v0.6 hardening.

**Members** (9):
- `hp-p0-*` (3): `hp-p0-hermes-agent-hardening`, `hp-p0-chain-break-investigation`, `hp-p0-writejsonatomic`
- `hp-p1-*` (4): `hp-p1-audit-update`, `hp-p1-docs`, `hp-p1-agent-evidence`, `hp-p1-lockmgr`
- `hp-audit-codex` — Codex-driven audit cycle that initiated the sweep
- `hp-registry` — registry hardening work

### 4. `hermesproof/` — HermesProof component sandboxes

**Match**: folder name starts with `hermesproof-`.

**Members** (6):
- `hermesproof-wizard-gates`, `hermesproof-wizard-sandbox`
- `hermesproof-queue-sandbox`, `hermesproof-queue-sandbox-v05`, `hermesproof-queue-next-task`
- `hermesproof-trigger-sandbox`

### 5. `source-os-60-apps/` — registry index (NOT a folder list)

**Match**: derived data — the canonical 60-app Source OS module registry from inside the Hermes3D codebase. Two files only: `REGISTRY.md` (master table + treemap SVG) and `README.md` (summary + bar chart).

### 6. `h3dos-wire-tasks/` — single-button UI wire-up lanes

**Match**: folder name starts with `h3dos-wire-`.

**Members** (18): all 18 listed `h3dos-wire-*` folders.

### 7. `h3dos-codex-tasks/` — Codex-driven app integration lanes

**Match**: folder name starts with `h3dos-codex-`.

**Members** (5): octoprint, fluidd, blender-cli, prusaslicer, triposr.

### 8. `merge-prs/` — cascade-merge resolution worktrees

**Match**: folder name starts with `merge-pr` followed by a digit.

**Members** (4): merge-pr23, merge-pr24, merge-pr27, merge-pr33.

### 9. `h3d-enhancements/` — Hermes3D enhancement / fix branches

**Match**: folder name starts with `h3d-` AND is not a wire/codex task.

**Members** (7): h3d-enh-screenshots, h3d-enh-readme-version, h3d-routing, h3d-3dprint-safety, h3d-stream-bootstrap, h3d-pr37, h3d-pr34.

### 10. `worktree-collections/` — multi-worktree umbrellas

**Match**: folder name starts with `_` AND contains multiple sub-worktrees managed by a runner.

**Members** (3): `_claude_worktrees` (29 children), `_codex_worktrees` (16 children), `_codex_audit_worktrees` (4 children).

### 11. `apps-vendored/` — local installations of slicers/modelers/desktop tools

**Match**: top-level folder is `apps/` (special case). Each immediate child is a vendored snapshot of a slicer, modeler, or desktop app integrated by Source OS.

**Members** (7): blender, blender-main, hermes-desktop-main, locale, OrcaSlicer-main, Printrun-printrun-2.2.0, PrusaSlicer-master.

### 12. `research/` — research scratchpad

**Match**: folder name is `_research`.

**Members** (1): `_research`.

---

## Status Vocabulary

When inspecting each folder, agents use a fixed set of status labels:

| Label | Meaning |
|---|---|
| `MERGED` | Branch has been merged to `origin/main` or `origin/develop`. PR closed-as-merged. |
| `OPEN` | Branch pushed to origin and a PR exists but is not yet merged. |
| `DRAFT` | Local-only branch with no origin push. |
| `ABANDONED` | PR closed without merge. Branch is stale. |
| `ARCHIVE` | Older snapshot kept for reference. Not actively maintained. |
| `SANDBOX` | Disposable test workspace. Not for merge. |
| `SNAPSHOT` | Vendored copy of an external project. Not a git repo. |
| `ACTIVE` | Currently in-flight; commits within last 7 days. |
| `INFERRED` | Value not directly observed; best-effort inference (e.g., backend endpoint guessed from filename). |

---

## Per-Folder Markdown Schema

Every per-folder markdown has at minimum:

1. **H1 title** — folder name as it appears under `G:\Github\`
2. **Purpose / Role** — 1–2 paragraphs explaining what this folder is and why it exists in H3D OS
3. **Status** — one of the labels above
4. **Branch & last commit** — `git branch --show-current` + `git log -1 --oneline`
5. **Key files** — top 5–10 with one-line descriptions
6. **Relationships** — links to other folders this one depends on or is depended on by
7. **Inline SVG diagram** — hand-written valid XML, between 400×200 and 700×500 px, illustrating the folder's role visually

Category READMEs additionally include:
- Master inventory table
- Master SVG (~700–900 px wide) showing all members of the category laid out together
- Cross-references to other categories where applicable

---

## SVG Conventions

Each SVG diagram embedded in this index is **inline `<svg>` XML**, not an external image file. This keeps the index self-contained and renderable on GitHub without binary attachments.

Style:
- Dark background (`#0e1116`) for the master diagrams
- Color-coded boxes by category (blue=core, green=agent, purple=hp/codex, orange=hermesproof/merge, etc.)
- Sans-serif font (`Segoe UI, Arial`) for portability
- Simple boxes + arrows; no external icon libraries

---

## What This Index Is NOT

- **Not a git history** — for that, use `git log` on each repo.
- **Not a PR tracker** — for that, use `gh pr list --repo <repo>`.
- **Not a code review** — per-folder markdowns describe purpose and structure, not code quality.
- **Not exhaustive of all G:\Github\** — it covers only folders modified 2026-04-27 → 2026-05-07 that are clearly Hermes3D OS.

---

## Maintenance Note

This index is a snapshot. To refresh:
1. Re-run the date-filter query: `Get-ChildItem G:\Github -Directory | Where-Object LastWriteTime -ge ...`
2. Compare against the inventory tables in each category README.
3. Add new folders to the appropriate category and update the master `00_INDEX.md` totals.
4. Update `02_EXCLUSIONS.md` with any newly excluded folders and the reason.
