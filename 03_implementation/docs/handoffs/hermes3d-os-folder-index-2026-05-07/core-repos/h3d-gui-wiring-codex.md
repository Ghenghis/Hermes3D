# h3d-gui-wiring-codex

## Role in H3D OS

`G:\Github\h3d-gui-wiring-codex` is a **sibling clone of `Ghenghis/Hermes3D.git`** dedicated to the multi-agent GUI-wiring contract — the workspace where the 20-agent Hermes3D-OS-tab-completion contract was executed. It mirrors the canonical 7-folder layout (`00_overview` … `06_release`), but its `03_implementation/` adds a fully expanded `docs/`, `proof/`, `source-lab/`, `tests/` tree and an explicit `ROADMAP.md` driven by `codex-master` for task `H3D-HERMES3D7-GUI-WIRING-2026-05-04`.

This is where the "every visible Hermes3D OS surface must be useful, dense, real, and responsive" contract is enforced. The directory contains Claude polish-audit lanes (docs, merge, no-fake, runtime, safety, security), a 6-agent polish-audit handoff, a 20-agent completion contract, an INTEGRATION report, a GitHub-sync plan, and the 9-file final Codex takeover bundle (executive summary, PR merge matrix, blocker fix queue, lock/worktree/branch ledger, runtime-truth audit, printer-safety audit, security/MCP audit, architecture diagrams, final release note).

Functionally, this repo is the **multi-agent coordination room** for Hermes3D's GUI surface: it tracks lock collisions (the H3D 20-agent lock-collision known-issue lives here), records audit verdicts, holds Playwright proofs, and is where agent dispatch contracts get signed before changes flow back to the canonical Hermes3D repo.

## Recent activity

Branch in this checkout: `chore/exclude-apps-folder` (HEAD).

```
485155b 2026-05-07 feat(agents): add provider execution artifacts
4f7d316 2026-05-07 feat(agents): add provider team assignment lane
30b42c0 2026-05-07 feat(agents): add proof-gated git shipping lane
128263b 2026-05-06 fix(agents): harden code operator lane
dc2070d 2026-05-06 docs(handoff): add Claude final audit takeover contract
c1a1064 2026-05-06 feat(agents): add MCP-locked code operator lane
f58a65a 2026-05-06 fix(ui): clear post-merge npm audit vulnerabilities (#82)
9bb39f3 2026-05-06 docs(handoff): final Codex takeover bundle — 9 audit/merge/lock files (#81)
6c08cc2 2026-05-06 audit(nofake-ui): 0 violations — 33 buttons wired + 0 lane TS errors (#79)
30661b9 2026-05-06 audit(docs): PR body completeness + ROADMAP truth + merge plan verification (#78)
```

Status: 5 dirty files (`audit_source_cli_agent_readiness.py`, `write_source_runtime_action_plan.py`, `agents.py`, `modules.py`, `module_runtime.py`) — uncommitted in-flight work.

## Branches

Same set as canonical `Hermes3D` (shared remote). All `claude/*`, `feature/*`, `foundation/*` branches enumerated in the Hermes3D index page.

Remote: `origin = https://github.com/Ghenghis/Hermes3D.git`

## Key directories (deep tree)

- `03_implementation/`
  - `adapter_registry/`, `config/` — same as canonical
  - `docs/` — full doc tree
    - `handoffs/` — `CLAUDE_20_AGENT_COMPLETION_CONTRACT.md`, `CLAUDE_6_AGENT_POLISH_AUDIT_2026-05-06.md`, `CLAUDE_FINAL_20_AGENT_AUDIT_HANDOFF_2026-05-06.md`, `GITHUB_SYNC_PLAN_2026-05-06.md`, `INTEGRATION_REPORT_2026-05-06.md`
    - `handoffs/audit/` — `MERGE_INTEGRITY_2026-05-06.md`, `NOFAKE_UI_AUDIT_RESULT_2026-05-06.md`, `PRINTER_SAFETY_2026-05-06.md`, `RELEASE_DOCS_2026-05-06.md`, `RUNTIME_TRUTH_2026-05-06.md`, `SECURITY_MCP_2026-05-06.md`
    - `handoffs/claude-final-audit-2026-05-06/` — 9 numbered files (`00_EXECUTIVE_TAKEOVER_SUMMARY.md` → `08_FINAL_CLAUDE_RELEASE_NOTE.md`)
  - `proof/` — Playwright + truth-gate proofs
  - `scripts/` — auditor scripts (`audit_source_cli_agent_readiness.py`, `write_source_runtime_action_plan.py`)
  - `source-lab/`, `src/`, `tests/`, `ui/`, `var/`, `ROADMAP.md`
- `agents/` — codex-master, claude-*, kilocode, windsurf agent role contracts
- `apps/` — staging area (NOT committed; same exclusion as canonical)
- `tmp/`, `var/`, `site/`, `schemas/`, `env/`, `scripts/`, `handoffs/`

## Key files

| File | Purpose |
| --- | --- |
| `03_implementation/ROADMAP.md` | codex-master tab-completion roadmap; printer policy (T1#1, T1#2, FLSUN S1) |
| `03_implementation/docs/handoffs/CLAUDE_20_AGENT_COMPLETION_CONTRACT.md` | 20-agent contract spec |
| `03_implementation/docs/handoffs/CLAUDE_FINAL_20_AGENT_AUDIT_HANDOFF_2026-05-06.md` | Audit handoff |
| `03_implementation/docs/handoffs/INTEGRATION_REPORT_2026-05-06.md` | Integration report |
| `03_implementation/docs/handoffs/claude-final-audit-2026-05-06/00_EXECUTIVE_TAKEOVER_SUMMARY.md` | Executive summary of state |
| `03_implementation/docs/handoffs/claude-final-audit-2026-05-06/03_LOCKS_WORKTREES_AND_BRANCHES.md` | Lock + worktree ledger |
| `03_implementation/docs/handoffs/audit/NOFAKE_UI_AUDIT_RESULT_2026-05-06.md` | 0 violations / 33 buttons wired audit |
| `03_implementation/docs/handoffs/audit/SECURITY_MCP_2026-05-06.md` | MCP security audit |
| `03_implementation/src/hermes3d/api/routes/agents.py` | Agent route (dirty) |
| `03_implementation/src/hermes3d/services/module_runtime.py` | Module runtime service (dirty) |

## Relationships to other H3D repos

- Shares **identical remote** with `Hermes3D` (sibling clone, not worktree). Branch sets coincide; this is the agent coordination room.
- Audit findings here drive PRs in the canonical `Hermes3D` repo.
- Hermes3D-OS GUI work in `apps/web/` consumes contracts validated here.
- The 20-agent contract referenced here generates the `Hermes3D-handoffs` worktree contents.

## Status

**ACTIVE** — primary multi-agent staging clone; 2026-05-07 commits today (provider execution artifacts, provider team lane).

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b1020"/>
  <rect x="170" y="120" width="160" height="60" fill="#065f46" stroke="#6ee7b7" stroke-width="2" rx="6"/>
  <text x="250" y="145" fill="#d1fae5" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">h3d-gui-wiring-codex</text>
  <text x="250" y="165" fill="#a7f3d0" font-family="sans-serif" font-size="10" text-anchor="middle">20-agent contract room</text>
  <rect x="20" y="30" width="120" height="50" fill="#1e3a8a" stroke="#60a5fa" stroke-width="1.5" rx="5"/>
  <text x="80" y="50" fill="#e0e7ff" font-family="sans-serif" font-size="11" text-anchor="middle" font-weight="bold">Hermes3D</text>
  <text x="80" y="68" fill="#a5b4fc" font-family="sans-serif" font-size="9" text-anchor="middle">canonical (sibling)</text>
  <rect x="360" y="30" width="120" height="50" fill="#7c2d12" stroke="#fdba74" stroke-width="1.5" rx="5"/>
  <text x="420" y="50" fill="#fed7aa" font-family="sans-serif" font-size="11" text-anchor="middle" font-weight="bold">Hermes3D-OS</text>
  <text x="420" y="68" fill="#fed7aa" font-family="sans-serif" font-size="9" text-anchor="middle">GUI consumer</text>
  <rect x="20" y="220" width="120" height="50" fill="#831843" stroke="#f472b6" stroke-width="1.5" rx="5"/>
  <text x="80" y="240" fill="#fbcfe8" font-family="sans-serif" font-size="10" text-anchor="middle">Hermes3D-handoffs</text>
  <text x="80" y="255" fill="#fbcfe8" font-family="sans-serif" font-size="9" text-anchor="middle">handoff worktree</text>
  <rect x="360" y="220" width="120" height="50" fill="#1e40af" stroke="#93c5fd" stroke-width="1.5" rx="5"/>
  <text x="420" y="245" fill="#dbeafe" font-family="sans-serif" font-size="10" text-anchor="middle">claude-/codex- agents</text>
  <line x1="170" y1="135" x2="140" y2="55" stroke="#60a5fa" stroke-width="1.5" stroke-dasharray="3 2"/>
  <line x1="330" y1="135" x2="360" y2="55" stroke="#fdba74" stroke-width="1.5"/>
  <line x1="170" y1="165" x2="140" y2="245" stroke="#f472b6" stroke-width="1.5"/>
  <line x1="330" y1="165" x2="360" y2="245" stroke="#93c5fd" stroke-width="1.5"/>
  <text x="145" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9">same remote</text>
  <text x="320" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9">contracts → GUI</text>
  <text x="135" y="205" fill="#cbd5e1" font-family="sans-serif" font-size="9">audit → handoff</text>
  <text x="320" y="205" fill="#cbd5e1" font-family="sans-serif" font-size="9">dispatched lanes</text>
</svg>
