# Hermes3D OS — Master Folder Index

**Generated**: 2026-05-07
**Scope**: All Hermes3D OS folders in `G:\Github\` modified between **2026-04-27** and **2026-05-07**
**Total folders indexed**: 71 (60 included + 11 excluded — see `02_EXCLUSIONS.md`)
**Total markdown files**: 83 (across 12 categories)
**Authored by**: 13 parallel sub-agents under `claude-orchestrator`
**Hermes task**: `a2a_1778147261453_661b606f`

---

## Top-Level Architecture

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 540" width="900" height="540" font-family="Segoe UI, Arial, sans-serif" font-size="13">
  <rect x="0" y="0" width="900" height="540" fill="#0e1116"/>
  <text x="450" y="28" fill="#fff" font-size="20" font-weight="bold" text-anchor="middle">Hermes3D OS — Folder Topology</text>
  <text x="450" y="50" fill="#aaa" font-size="12" text-anchor="middle">G:\Github\ — 60 folders, 4-27 → 5-7</text>

  <!-- Core ring -->
  <rect x="350" y="80" width="200" height="60" rx="6" fill="#1f6feb" stroke="#388bfd"/>
  <text x="450" y="105" fill="#fff" text-anchor="middle" font-weight="bold">Core repos (5)</text>
  <text x="450" y="125" fill="#cde" text-anchor="middle" font-size="11">Hermes3D · h3d-gui-wiring-codex · Hermes3D-OS</text>

  <!-- Agent infra ring -->
  <rect x="50" y="170" width="200" height="60" rx="6" fill="#238636" stroke="#3fb950"/>
  <text x="150" y="195" fill="#fff" text-anchor="middle" font-weight="bold">Agent infra (5)</text>
  <text x="150" y="215" fill="#cfe" text-anchor="middle" font-size="11">hermes-agent · MCP-lock · bridge</text>

  <!-- HP protocol -->
  <rect x="270" y="170" width="160" height="60" rx="6" fill="#8957e5" stroke="#a371f7"/>
  <text x="350" y="195" fill="#fff" text-anchor="middle" font-weight="bold">HP protocol (9)</text>
  <text x="350" y="215" fill="#dce" text-anchor="middle" font-size="11">P0/P1 hardening · audit</text>

  <!-- HermesProof -->
  <rect x="450" y="170" width="160" height="60" rx="6" fill="#bf8700" stroke="#dba000"/>
  <text x="530" y="195" fill="#fff" text-anchor="middle" font-weight="bold">HermesProof (6)</text>
  <text x="530" y="215" fill="#fed" text-anchor="middle" font-size="11">truth-gate · queue · trigger</text>

  <!-- Source OS registry -->
  <rect x="630" y="170" width="220" height="60" rx="6" fill="#cf222e" stroke="#ff5050"/>
  <text x="740" y="195" fill="#fff" text-anchor="middle" font-weight="bold">Source OS registry (60 apps)</text>
  <text x="740" y="215" fill="#fcc" text-anchor="middle" font-size="11">slicers · modelers · firmware · 3D-gen</text>

  <!-- Wire tasks -->
  <rect x="50" y="280" width="180" height="60" rx="6" fill="#0e8090" stroke="#39c5cf"/>
  <text x="140" y="305" fill="#fff" text-anchor="middle" font-weight="bold">UI wire tasks (18)</text>
  <text x="140" y="325" fill="#ceefef" text-anchor="middle" font-size="11">single-button feature lanes</text>

  <!-- Codex tasks -->
  <rect x="250" y="280" width="180" height="60" rx="6" fill="#a371f7" stroke="#bc8cff"/>
  <text x="340" y="305" fill="#fff" text-anchor="middle" font-weight="bold">Codex tasks (5)</text>
  <text x="340" y="325" fill="#e9def8" text-anchor="middle" font-size="11">app integration lanes</text>

  <!-- Merge PRs -->
  <rect x="450" y="280" width="160" height="60" rx="6" fill="#fb8500" stroke="#ffa730"/>
  <text x="530" y="305" fill="#fff" text-anchor="middle" font-weight="bold">Merge PRs (4)</text>
  <text x="530" y="325" fill="#ffe6cc" text-anchor="middle" font-size="11">cascade resolution worktrees</text>

  <!-- h3d enhancements -->
  <rect x="630" y="280" width="220" height="60" rx="6" fill="#6e7681" stroke="#8b949e"/>
  <text x="740" y="305" fill="#fff" text-anchor="middle" font-weight="bold">h3d enhancements (7)</text>
  <text x="740" y="325" fill="#dee" text-anchor="middle" font-size="11">routing · safety · stream · docs</text>

  <!-- Worktree collections -->
  <rect x="200" y="380" width="220" height="60" rx="6" fill="#347d39" stroke="#56d364"/>
  <text x="310" y="405" fill="#fff" text-anchor="middle" font-weight="bold">Worktree collections (3)</text>
  <text x="310" y="425" fill="#cfe" text-anchor="middle" font-size="11">_claude_ · _codex_ · _codex_audit_</text>

  <!-- Apps vendored -->
  <rect x="450" y="380" width="200" height="60" rx="6" fill="#bf8700" stroke="#dba000"/>
  <text x="550" y="405" fill="#fff" text-anchor="middle" font-weight="bold">Apps vendored (7)</text>
  <text x="550" y="425" fill="#fed" text-anchor="middle" font-size="11">Blender · slicers · Printrun · Hermes Desktop</text>

  <!-- Research -->
  <rect x="680" y="380" width="160" height="60" rx="6" fill="#0e8090" stroke="#39c5cf"/>
  <text x="760" y="405" fill="#fff" text-anchor="middle" font-weight="bold">Research (1)</text>
  <text x="760" y="425" fill="#ceefef" text-anchor="middle" font-size="11">_research scratchpad</text>

  <!-- Lines from core to all -->
  <line x1="450" y1="140" x2="150" y2="170" stroke="#888" stroke-width="1" opacity="0.5"/>
  <line x1="450" y1="140" x2="350" y2="170" stroke="#888" stroke-width="1" opacity="0.5"/>
  <line x1="450" y1="140" x2="530" y2="170" stroke="#888" stroke-width="1" opacity="0.5"/>
  <line x1="450" y1="140" x2="740" y2="170" stroke="#888" stroke-width="1" opacity="0.5"/>
  <line x1="450" y1="140" x2="140" y2="280" stroke="#888" stroke-width="1" opacity="0.3"/>
  <line x1="450" y1="140" x2="340" y2="280" stroke="#888" stroke-width="1" opacity="0.3"/>
  <line x1="450" y1="140" x2="530" y2="280" stroke="#888" stroke-width="1" opacity="0.3"/>
  <line x1="450" y1="140" x2="740" y2="280" stroke="#888" stroke-width="1" opacity="0.3"/>

  <!-- Footer -->
  <text x="450" y="500" fill="#aaa" font-size="11" text-anchor="middle">12 categories · 83 markdowns · ~1.08 GB vendored apps · 60-app registry · 49 worktrees</text>
  <text x="450" y="520" fill="#666" font-size="10" text-anchor="middle">Excluded: kilocode-Azure2, contract-kit-v17* (2x), TRELLIS.2, Agentic-Modeler, _repo_rescue_evidence — see 02_EXCLUSIONS.md</text>
</svg>
```

---

## Categories

| # | Category | Folders | Files | Description |
|---|---|---|---|---|
| 1 | [`core-repos/`](core-repos/README.md) | 5 | 6 | Main Hermes3D, h3d-gui-wiring-codex, Hermes3D-OS, worktree umbrella, handoffs |
| 2 | [`agent-infra/`](agent-infra/README.md) | 5 | 6 | Hermes Agent + MCP infrastructure (orchestrator, bridge, sandboxes, fresh clone, atomic-hermes) |
| 3 | [`hp-protocol/`](hp-protocol/README.md) | 9 | 10 | HermesProof P0/P1 hardening sweep + audit work (lockmgr, evidence, atomic writes, chain-break RCA) |
| 4 | [`hermesproof/`](hermesproof/README.md) | 6 | 7 | HermesProof component sandboxes (wizard, queue, trigger) — 5 placeholders + 1 fixture |
| 5 | [`source-os-60-apps/`](source-os-60-apps/README.md) | (registry) | 2 | The canonical 60-app Source OS module registry — derived from YAML truth |
| 6 | [`h3dos-wire-tasks/`](h3dos-wire-tasks/README.md) | 18 | 19 | Single-button UI wire-up lanes (artifacts row click, agents list, jobs row click, etc.) |
| 7 | [`h3dos-codex-tasks/`](h3dos-codex-tasks/README.md) | 5 | 6 | Codex-driven app integration lanes (octoprint, fluidd, blender-cli, prusaslicer, triposr) |
| 8 | [`merge-prs/`](merge-prs/README.md) | 4 | 5 | Cascade-merge resolution worktrees for HermesProof PRs #23, #24, #27, #33 |
| 9 | [`h3d-enhancements/`](h3d-enhancements/README.md) | 7 | 8 | Hermes3D enhancement / fix branches (safety gates, routing, stream-bootstrap, screenshots, version) |
| 10 | [`worktree-collections/`](worktree-collections/README.md) | 3 (49 sub) | 4 | `_claude_worktrees` (29) + `_codex_worktrees` (16) + `_codex_audit_worktrees` (4) |
| 11 | [`apps-vendored/`](apps-vendored/README.md) | 7 | 8 | Vendored slicers/modelers/desktop apps in `G:\Github\apps\` (~1.08 GB total) |
| 12 | [`research/`](research/README.md) | 1 | 2 | `_research/` scratchpad — embedded `atomic-hermes/` clone of NousResearch hermes-agent |

---

## Headline Findings (per category)

### Core repos
- **`Hermes3D`** is the canonical FastAPI + MCP server hub on `Ghenghis/Hermes3D`. 30+ branches.
- **`h3d-gui-wiring-codex`** is a sibling clone where the 20-agent contract ran. Hosts ROADMAP + 9-file Codex takeover bundle.
- **`Hermes3D-OS`** is an independent repo (`Ghenghis/Hermes3D-OS.git`) with `apps/web` SPA + `apps/api` FastAPI bridge.
- **`Hermes3D-worktrees`** is an umbrella dir, NOT a repo — contains `lm-studio-default` sub-worktree.
- **`Hermes3D-handoffs`** is a frozen worktree of canonical Hermes3D pinned to `docs/cp5.1-c-handoff`.

### Agent infra
- **`hermes3d-mcp-lock-orchestrator`** is the **active primary** orchestrator (HermesProof v0.7.0, 44 MCP tools, 35 truth-gates, Sigstore-signed PROOF).
- **`hp-hermes-agent-bridge`** is the predecessor v0.6.0 with 36 MCP tools (8 fewer: A2A, dispatch_recommend, record_outcome, record_task, list_agents).
- **`hermes-agent-fresh`** is a vendored NousResearch Hermes Agent v0.12.0 reference.
- **`atomic-hermes`** is an AtomicBot-ai macOS Electron fork of the Hermes Desktop.
- **`hermes3d-mcp-test-sandbox`** is the disposable smoke-test fixture with a populated `.hermes3d_orchestrator/` state dir.

### HP protocol
- All 9 are clones/branches of HermesProof. Activity timeline (2026-05-03):
  1. `hp-audit-codex` 09:36 (audit)
  2. `hp-registry`, `hp-p0-writejsonatomic`, `hp-p0-chain-break-investigation` (P0)
  3. `hp-p1-lockmgr`, `hp-p1-agent-evidence`, `hp-p1-docs`, `hp-p1-audit-update` (P1)
  4. `hp-p0-hermes-agent-hardening` 13:25 (main integration)
- PRs landed: #20, #25, #29, #32, #33, #41, #44, #46, #47, #48, #52.

### HermesProof
- Only `hermesproof-trigger-sandbox` has substance — full captured run with hash-chained evidence ledger (sha256 prev_hash → entry_hash chain). Canonical fixture for the proof-event shape.
- 5 of 6 are bare init placeholders.

### Source OS 60-app registry
- **Exact count: 60** across 11 sections (modelers 13, slicers 11, print_farm 10, agents 7, firmware 6, three_d_generation 6, hardware 3, library 1, materials 1, research 1, utilities 1).
- `klipper` appears in both `print_farm` and `firmware` (resolved by loader as `firmware_klipper`).
- Truth source: `Hermes3D-GUI-Wiring-Contract-Kit/03_REPO_REGISTRY/external_repos_registry.yaml` (439 lines).
- Only **5 of 60** modules have a dedicated `h3dos-codex-*` folder; the other 55 use the generic loader resolving them via `source-lab/sources/<section>/<safe-name>`.

### h3dos-wire-tasks
- 18 folders, **5 MERGED to develop** (#38, #39, #41, #44, #46), **5 OPEN on develop** (#28, #30, #32, #34, #35), 8 still local-branch only.
- Dominant pattern: `GET /api/workspace` → click handler → `openActionWindow(kind, entity)`.
- Real backend endpoints discovered (not inferred): `/api/artifacts/{id}/download`, `/api/agents/list`, `/api/agents/{id}/health`, `/api/jobs/{id}/cancel`, `/api/observe/mute/{id}`, `/api/observe/stream/{id}`, etc.
- Conflict scar: `dashboard-events-tail` lost its click handler during a `-X theirs` merge (restored in develop `439699c`).

### h3dos-codex-tasks
- All 5 are branches of `Hermes3D-OS` sharing `apps/api/hermes3d_api/source_install.py` (~636 LOC, 8 `subprocess.run` sites, 6 install methods).
- PRs #21–#25 form a linear stack; only #21 is on `origin/main`. Others (octoprint, fluidd, blender-cli, prusaslicer) are local-only.
- Only **triposr** (#25) is on origin.

### Merge PRs
- All 4 `merge-pr*` worktrees belong to `Ghenghis/HermesProof`, NOT Hermes3D.
- All 4 PRs MERGED 2026-05-03 (HermesProof v0.6 truth-gate wave).
- Cascade order: #23 → #24 → #27 → #33. Each later branch had to forward-merge predecessors.
- Conflict pattern: UNION for `package.json`, `scripts/truth-gates.mjs`; TAKE-THEIRS for `PROOF/latest.json*`.

### h3d-enhancements
- 4 MERGED, 2 OPEN, 1 ABANDONED. Diffs against `origin/develop` (main shares no history — v5.3.0 sprint convention).
- `h3d-pr37` was closed without merge — partial scaffolds may have re-landed elsewhere.
- `h3d-enh-screenshots` has zero new commits beyond develop tip; all work uncommitted in working tree.

### Worktree collections
- **49 worktrees total**, all linked-worktree `.git` files (none are full repos).
- `_claude_worktrees` (29) — 20 implementation lanes + 6 polish-audit + 2 handoff/index + 1 CI fix. All active.
- `_codex_worktrees` (16) — 9 branch-tracking + 6 detached PR-audit + 1 post-claude-merged. 6 detached HEAD.
- `_codex_audit_worktrees` (4) — 4 detached PR-audit pairs (PR #35 + PR #37, audit/main pairs).

### Apps vendored (`G:\Github\apps\`)
- 7 vendored snapshots, ~1.08 GB total. **None are git repos** — all are extracted/downloaded snapshots.
- `blender` + `blender-main` (282 MB each, GPLv3, CMake/C++/Python).
- `OrcaSlicer-main` (293 MB, SoftFever fork v2.4.0-dev).
- `PrusaSlicer-master` (201 MB, v2.9.5-beta2).
- `Printrun-printrun-2.2.0` (3.7 MB, Python wxPython).
- `hermes-desktop-main` (17 MB, Electron 39 + React 19 v0.2.2, MIT).
- `locale` (0.6 MB, gettext overlay for Printrun).

### Research
- `_research/` is a scratchpad with 1 embedded git repo: `atomic-hermes/` (NousResearch hermes-agent rebuild by AtomicBot-ai).
- 12 topic clusters: agent core, provider adapters, tools, gateway, skills (25), plugins, protocols (ACP/MCP), scheduler, GUI, CLI, build, releases (v0.2.0–v0.11.0).

---

## How to Read This Index

1. **Start here** (`00_INDEX.md`) for the bird's-eye view.
2. **`01_TAXONOMY.md`** — the rules used to classify each folder.
3. **`02_EXCLUSIONS.md`** — folders that were intentionally NOT indexed and why.
4. **Category READMEs** — each `<category>/README.md` has its own master SVG and inventory table.
5. **Per-folder markdowns** — each `<category>/<folder>.md` has detailed inspection: purpose, status, branch, key files, SVG diagram, relationships.

---

## Conventions Used in Per-Folder Markdowns

- **`MERGED`** — branch landed on `origin/main` or `origin/develop`.
- **`OPEN`** — branch pushed to origin but not yet merged.
- **`DRAFT`** — local-only branch (no origin push).
- **`ABANDONED`** — PR closed without merge, branch stale.
- **`ARCHIVE`** — older snapshot kept for reference.
- **`SANDBOX`** — disposable test workspace.
- **`SNAPSHOT`** — vendored copy, not a git repo.
- **`INFERRED`** — value not directly observed; reasonable inference.

---

*Index built 2026-05-07 by 13 parallel `general-purpose` sub-agents under task `a2a_1778147261453_661b606f`. Total work: ~5,367 seconds CPU, ~931K tokens.*
