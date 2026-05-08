# Hermes3D-handoffs

## Role in H3D OS

`G:\Github\Hermes3D-handoffs` is a **`git worktree` of the canonical `Hermes3D` repo**, pinned to branch `docs/cp5.1-c-handoff` so the architect handoff brief (`HANDOFF_TO_CODEX_CP5.1-C.md`) and the surrounding handoff bundle stay reachable without disturbing other working trees. The `.git` is a file (not a directory) that reads `gitdir: G:/Github/Hermes3D/.git/worktrees/Hermes3D-handoffs`, confirming it shares the canonical's object store.

This worktree is the **handoff-document staging area** for Hermes3D's CP-phase work (Codex Phase / completion-phase contracts). Its `handoffs/` directory contains the master handoff queue: the `PERPETUAL_MASTER_INDEX.md`, the `PROJECT_COMPLETION_ROADMAP.md`, and every `HANDOFF_TO_CODEX_*.md` brief — covering blender-mcp-native audit, continue-from-unblock, CP5.1-C architect, local intelligence, LM Studio, Mnemosyne recall, service health, HermesProof 0.6 gate pack, overnight autopilot, perpetual wakeup, Phase 5.1 wrap, and SOTA marketing v2. Plus `HANDOFF_TO_CLAUDE_OVERNIGHT_COMPLETE.md` and `HERMES_AGENT_ENABLE.md`.

Functionally it is the read-stable view of architect briefs that Codex/Claude lanes can reference even while other branches are being heavily edited in parallel worktrees.

## Recent activity

Branch: `docs/cp5.1-c-handoff` (HEAD).

```
d7336a5 2026-05-02 docs(handoff): HANDOFF_TO_CODEX_CP5.1-C.md (architect brief)
e25fe7e 2026-05-02 Merge pull request #17 from Ghenghis/feat/phase-3-4-real-provider-probes
feb9f4f 2026-05-02 fix(phase3.4): expand proof to all six scenarios + tighten verifier (CP3.4-E1)
a10d7b7 2026-05-02 chore(phase3.4): proof bundle + completion report + PR body (CP3.4-E)
79aadaf 2026-05-02 feat(phase3.4): add providers/health bridge route + ui dot + playwright (CP3.4-D)
1f16a73 2026-05-02 feat(phase3.4): wire R9/R10 + provider.probe capability + cli + integration (CP3.4-C)
5023e70 2026-05-02 feat(phase3.4): add probe gateway + minimax/deepseek adapter substrate (CP3.4-B)
2fe40b5 2026-05-02 feat(phase3.4): add Phase 3.4 plan + ADR-012 + extended policy schema (CP3.4-A)
6231d33 2026-05-02 Merge pull request #16 from Ghenghis/feat/phase-3-3-llm-planner-gateway
e1df84d 2026-05-02 chore: remove accidental file from PR
```

Status: clean.

## Branches

This worktree is pinned to `docs/cp5.1-c-handoff`. Inherits the full branch set of the canonical `Hermes3D` repo (see `core-repos/Hermes3D.md`).

Remote: `origin = https://github.com/Ghenghis/Hermes3D.git` (shared with canonical).

## Key directories (deep tree)

- `00_overview/` … `06_release/` — same as canonical Hermes3D layout (frozen at 2026-05-02 state)
- `agents/` — agent role contracts at the CP-5.1 cut
- `env/`, `schemas/`, `scripts/`
- `handoffs/` — **the unique payload of this worktree**
  - Top-level briefs:
    - `HANDOFF_TO_CLAUDE_OVERNIGHT_COMPLETE.md`
    - `HANDOFF_TO_CODEX_BLENDER_MCP_AUDIT.md`
    - `HANDOFF_TO_CODEX_CONTINUE_FROM_UNBLOCK.md`
    - `HANDOFF_TO_CODEX_CP5.1-C.md`
    - `HANDOFF_TO_CODEX_HERMES3D_LOCAL_INTELLIGENCE.md`
    - `HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md`
    - `HANDOFF_TO_CODEX_HERMES3D_MNEMOSYNE_RECALL.md`
    - `HANDOFF_TO_CODEX_HERMES3D_SERVICE_HEALTH.md`
    - `HANDOFF_TO_CODEX_HERMESPROOF_0.6_GATE_PACK.md`
    - `HANDOFF_TO_CODEX_OVERNIGHT_AUTOPILOT.md`
    - `HANDOFF_TO_CODEX_PERPETUAL_WAKEUP.md`
    - `HANDOFF_TO_CODEX_PHASE5_1_WRAP_AND_RELEASE_INFRA.md`
    - `HANDOFF_TO_CODEX_SOTA_MARKETING_V2.md`
    - `HERMES_AGENT_ENABLE.md`
    - `PERPETUAL_MASTER_INDEX.md`
    - `PROJECT_COMPLETION_ROADMAP.md`
  - `STREAM/` — streaming handoff substream
- `hermes3d_gui_contract_kit_v4.1/`

Note: Unlike the canonical or h3d-gui-wiring-codex checkouts, this one does NOT have an `apps/`, `site/`, `tmp/`, or `var/` at top level — it is a frozen architectural / docs view.

## Key files

| File | Purpose |
| --- | --- |
| `handoffs/HANDOFF_TO_CODEX_CP5.1-C.md` | Architect brief for completion-phase 5.1-C (the reason this branch exists) |
| `handoffs/PERPETUAL_MASTER_INDEX.md` | Master index of all handoff briefs |
| `handoffs/PROJECT_COMPLETION_ROADMAP.md` | Project-wide completion roadmap |
| `handoffs/HANDOFF_TO_CODEX_HERMESPROOF_0.6_GATE_PACK.md` | HermesProof 0.6 gate-pack contract |
| `handoffs/HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md` | Originating brief for the lm-studio-default worktree's ADR-015 |
| `handoffs/HANDOFF_TO_CODEX_HERMES3D_SERVICE_HEALTH.md` | Service-health gate brief |
| `handoffs/HANDOFF_TO_CODEX_OVERNIGHT_AUTOPILOT.md` | Overnight autopilot lane |
| `handoffs/HANDOFF_TO_CLAUDE_OVERNIGHT_COMPLETE.md` | Claude-side overnight completion brief |
| `handoffs/HERMES_AGENT_ENABLE.md` | Hermes Agent enablement contract |
| `README.md` | Hermes3D project README at CP-5.1 cut |

## Relationships to other H3D repos

- **Worktree of `Hermes3D`** (canonical). Shares `.git`; branch operations land in canonical's object store.
- The `handoffs/HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md` brief here is the originating contract for the `Hermes3D-worktrees/lm-studio-default/` ADR-015 work.
- Briefs here are referenced by `h3d-gui-wiring-codex/03_implementation/docs/handoffs/` audit bundles (the 20-agent contract chain).
- Independent of `Hermes3D-OS` (different remote, different responsibility — this is the docs-stable architect view, not the GUI consumer).

## Status

**SNAPSHOT / FROZEN HANDOFF VIEW** — no commits since 2026-05-02; intentionally pinned to `docs/cp5.1-c-handoff` so architect briefs remain stable while sibling worktrees iterate. Active in the sense that other lanes read it; not actively edited itself.

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b1020"/>
  <rect x="170" y="20" width="160" height="50" fill="#1e3a8a" stroke="#60a5fa" stroke-width="2" rx="6"/>
  <text x="250" y="40" fill="#e0e7ff" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">Hermes3D</text>
  <text x="250" y="58" fill="#a5b4fc" font-family="sans-serif" font-size="9" text-anchor="middle">canonical .git store</text>
  <rect x="160" y="120" width="180" height="55" fill="#831843" stroke="#f472b6" stroke-width="2" rx="6"/>
  <text x="250" y="142" fill="#fbcfe8" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">Hermes3D-handoffs</text>
  <text x="250" y="158" fill="#fbcfe8" font-family="sans-serif" font-size="10" text-anchor="middle">worktree @ docs/cp5.1-c-handoff</text>
  <text x="250" y="170" fill="#f9a8d4" font-family="sans-serif" font-size="9" text-anchor="middle">SNAPSHOT</text>
  <rect x="20" y="220" width="140" height="50" fill="#7c2d12" stroke="#fdba74" stroke-width="1.5" rx="5"/>
  <text x="90" y="240" fill="#fed7aa" font-family="sans-serif" font-size="10" text-anchor="middle">lm-studio-default</text>
  <text x="90" y="255" fill="#fed7aa" font-family="sans-serif" font-size="9" text-anchor="middle">consumes LM Studio brief</text>
  <rect x="340" y="220" width="140" height="50" fill="#065f46" stroke="#6ee7b7" stroke-width="1.5" rx="5"/>
  <text x="410" y="240" fill="#d1fae5" font-family="sans-serif" font-size="10" text-anchor="middle">h3d-gui-wiring-codex</text>
  <text x="410" y="255" fill="#a7f3d0" font-family="sans-serif" font-size="9" text-anchor="middle">references audit briefs</text>
  <line x1="250" y1="70" x2="250" y2="120" stroke="#f472b6" stroke-width="2"/>
  <text x="260" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9">.git/worktrees/</text>
  <line x1="190" y1="175" x2="120" y2="220" stroke="#fdba74" stroke-width="1.5" stroke-dasharray="3 2"/>
  <line x1="310" y1="175" x2="380" y2="220" stroke="#6ee7b7" stroke-width="1.5" stroke-dasharray="3 2"/>
  <text x="40" y="200" fill="#cbd5e1" font-family="sans-serif" font-size="9">brief→impl</text>
  <text x="360" y="200" fill="#cbd5e1" font-family="sans-serif" font-size="9">brief→audit</text>
</svg>
