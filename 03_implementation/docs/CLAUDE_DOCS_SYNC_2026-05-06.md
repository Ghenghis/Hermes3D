# Claude Docs Sync — 2026-05-06

Lane: `H3D-CLAUDE-DOCS-PROOF` (Lane 18 of the Hermes3D 20-Agent Completion Contract)
Owner: `claude-docs-proof`
Branch: `claude/docs-proof`
Base: `feat/hermes3d-7-complete-gui-repo-wiring`

This file is a Claude-authored companion to `03_implementation/ROADMAP.md`.
It records the live Hermes3D OS baseline as of 2026-05-06 without editing
files held by another lane's active Hermes lock. ROADMAP.md is owned by
`codex-master` under task `H3D-HERMES3D7-GUI-WIRING-2026-05-04` at the time
of this sync, so this lane only adds proof and a docs-sync note.

## Baseline Commits Landed (last 5)

| SHA | Subject |
| --- | --- |
| `be753d9e` | test(e2e): add live GUI and no-fake proof coverage |
| `e38b38c9` | feat(source-os): add adapter schemas, source audits, and runtime proof |
| `a13fd442` | feat(ui): wire live Hermes3D tabs and remove mock UX |
| `3b9235ba` | feat(api): add live Hermes3D backend routes and proof services |
| `c9b1afda` | docs(contract): sync Hermes3D completion roadmap and Claude handoffs |

These five commits are the shared baseline that all 20 Claude lanes branch
from. Each lane operates in its own worktree and only touches its declared
file set.

## Tab Inventory (from `03_implementation/ui/src/app/routes.tsx`)

`TABS` exports 16 tabs. `PRIMARY_TABS` excludes `roadmap` and exports 15.
Each id maps to a real `.tsx` file under `03_implementation/ui/src/tabs/`.

| # | id | label | tab file |
| --- | --- | --- | --- |
| 1 | `source_os` | Source OS | `SourceOS.tsx` |
| 2 | `dashboard` | Dashboard | `Dashboard.tsx` |
| 3 | `autopilot` | Autopilot | `Autopilot.tsx` |
| 4 | `design` | Design | `Design.tsx` |
| 5 | `gen3d` | 3D Generation | `Gen3D.tsx` |
| 6 | `jobs` | Jobs | `Jobs.tsx` |
| 7 | `printers` | Printers | `Printers.tsx` |
| 8 | `observe` | Observe | `Observe.tsx` |
| 9 | `voice` | Voice | `Voice.tsx` |
| 10 | `agents` | Agents | `Agents.tsx` |
| 11 | `learning` | Learning | `Learning.tsx` |
| 12 | `artifacts` | Artifacts | `Artifacts.tsx` |
| 13 | `approvals` | Approvals | `Approvals.tsx` |
| 14 | `plugins` | Plugins | `Plugins.tsx` |
| 15 | `settings` | Settings | `Settings.tsx` |
| 16 | `roadmap` | Roadmap | `Roadmap.tsx` |

Tab ledger status (mirrors `03_implementation/ROADMAP.md` as of this sync):

- DONE: Dashboard, Simple GUI, Observe, Agents rail/chat, Artifacts, Jobs,
  Approvals.
- IN_PROGRESS: Source OS, Plugins, Printers, Settings, Autopilot, Learning,
  Voice, Design, 3D Generation, Roadmap.

No tab is claimed live in this doc unless it is either present in the
ROADMAP ledger above or has a backing spec under
`03_implementation/ui/tests/e2e/`. As of this sync the e2e directory
contains `live-gui.spec.ts`.

## Printer Policy (live, as of 2026-05-06)

- FLSUN S1 — `192.168.0.12` — camera read-only. No move, upload, print,
  or test. UI must show locked status until the user changes it.
- T1 #1 — `192.168.0.10` — Moonraker/Klipper. Testable only via
  policy-gated backend routes.
- T1 #2 — `192.168.0.11` — Moonraker/Klipper. Testable only via
  policy-gated backend routes.
- FLSUN V400 — `192.168.0.34` — Moonraker/Klipper. Testable via
  policy-gated backend routes; USB webcam URL is configured and read
  through Observe.

Secrets used by the backend (Azure Speech, Hermes Agent runtime, proof
signing keys, etc.) are loaded from `G:/private/.env` at runtime only.
They are never committed, never echoed, and never sent to the frontend.

## Proof File

`03_implementation/proof/DOCS_SYNC_2026-05-06.json` records the same
baseline (commit shas, tab list, printer policy, files changed,
hermes task id). That JSON is the machine-readable proof for this lane.

## Hermes Locks Used By This Lane

Owner: `claude-docs-proof`
Task: `H3D-CLAUDE-DOCS-PROOF`
Files locked:

- `03_implementation/proof/DOCS_SYNC_2026-05-06.json`
- `03_implementation/docs/CLAUDE_DOCS_SYNC_2026-05-06.md`
- `README.md`

ROADMAP.md was intentionally not locked or edited because an active
non-stale lock from `codex-master` was present at sync time.
