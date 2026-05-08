# Core repos — Hermes3D OS folder index (2026-05-07)

This index covers the five top-level directories under `G:\Github\` that constitute the Hermes3D OS development surface. Two GitHub remotes back the entire system:

- `Ghenghis/Hermes3D.git` (canonical methodology + agent contracts + Python service + UI)
- `Ghenghis/Hermes3D-OS.git` (standalone GUI shell + apps/api FastAPI bridge)

The five directories include one umbrella (`Hermes3D-worktrees`) and one shared-`.git` worktree (`Hermes3D-handoffs`); the remaining three are independent checkouts.

## Repos

| Folder | Remote | Branch (this checkout) | Role | Status |
| --- | --- | --- | --- | --- |
| [Hermes3D](./Hermes3D.md) | Ghenghis/Hermes3D | `chore/exclude-apps-folder` | Canonical 7-folder methodology + Python `hermes3d` package + React/Vite UI + agent contracts. Source-of-truth for Hermes3D OS. | ACTIVE |
| [h3d-gui-wiring-codex](./h3d-gui-wiring-codex.md) | Ghenghis/Hermes3D | `chore/exclude-apps-folder` | Sibling clone where the 20-agent GUI-wiring contract executes; carries audit handoffs, ROADMAP, and the 9-file final Codex takeover bundle. | ACTIVE |
| [Hermes3D-OS](./Hermes3D-OS.md) | Ghenghis/Hermes3D-OS | `develop` | Standalone GUI shell (`apps/web`) + FastAPI bridge (`apps/api`) + Playwright E2E + 16 OS pages. Consumer of Hermes3D contracts. | ACTIVE |
| [Hermes3D-worktrees](./Hermes3D-worktrees.md) | (umbrella) | N/A | Holds additional `git worktree` checkouts of canonical Hermes3D; currently 1 sub-worktree (`lm-studio-default` on `feat/cp-h3d-lm-studio-default`, ADR-015). | ACTIVE (1 worktree) |
| [Hermes3D-handoffs](./Hermes3D-handoffs.md) | Ghenghis/Hermes3D (worktree) | `docs/cp5.1-c-handoff` | Frozen handoff-docs view; pins the architect briefs and `HANDOFF_TO_CODEX_*.md` queue stable while other lanes iterate. | SNAPSHOT |

## Topology

- **Hermes3D** is the hub: its `.git` store is shared by `Hermes3D-handoffs` (a worktree) and `Hermes3D-worktrees/lm-studio-default/` (a worktree).
- **h3d-gui-wiring-codex** is a SEPARATE clone of the same remote — branch operations there require a `git fetch` to reach the canonical clone.
- **Hermes3D-OS** is a fully independent repo on a different remote, but it consumes contracts and bridges to Hermes3D's MCP / FastAPI surface via `apps/api/hermes3d_api/services/hermes_bridge.py` (currently uncommitted in-flight).
- Multi-agent flow: briefs are written in `Hermes3D-handoffs/handoffs/` → contracts are signed and audited in `h3d-gui-wiring-codex/03_implementation/docs/handoffs/` → implementation lands in `Hermes3D` branches and propagates to `Hermes3D-OS` GUI.

## SVG: how the five directories relate

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400">
  <rect width="600" height="400" fill="#0b1020"/>

  <!-- Hermes3D (hub) -->
  <rect x="225" y="170" width="150" height="60" fill="#1e3a8a" stroke="#60a5fa" stroke-width="2.5" rx="8"/>
  <text x="300" y="195" fill="#e0e7ff" font-family="sans-serif" font-size="14" text-anchor="middle" font-weight="bold">Hermes3D</text>
  <text x="300" y="212" fill="#a5b4fc" font-family="sans-serif" font-size="10" text-anchor="middle">canonical .git store</text>
  <text x="300" y="223" fill="#a5b4fc" font-family="sans-serif" font-size="9" text-anchor="middle">Ghenghis/Hermes3D</text>

  <!-- Hermes3D-handoffs (worktree, top-left) -->
  <rect x="30" y="40" width="160" height="55" fill="#831843" stroke="#f472b6" stroke-width="2" rx="6"/>
  <text x="110" y="62" fill="#fbcfe8" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">Hermes3D-handoffs</text>
  <text x="110" y="78" fill="#fbcfe8" font-family="sans-serif" font-size="9" text-anchor="middle">worktree @ docs/cp5.1-c-handoff</text>
  <text x="110" y="89" fill="#f9a8d4" font-family="sans-serif" font-size="9" text-anchor="middle">SNAPSHOT</text>

  <!-- h3d-gui-wiring-codex (sibling clone, top-right) -->
  <rect x="410" y="40" width="160" height="55" fill="#065f46" stroke="#6ee7b7" stroke-width="2" rx="6"/>
  <text x="490" y="62" fill="#d1fae5" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">h3d-gui-wiring-codex</text>
  <text x="490" y="78" fill="#a7f3d0" font-family="sans-serif" font-size="9" text-anchor="middle">sibling clone (same remote)</text>
  <text x="490" y="89" fill="#a7f3d0" font-family="sans-serif" font-size="9" text-anchor="middle">20-agent contract</text>

  <!-- Hermes3D-worktrees (umbrella, bottom-left) -->
  <rect x="30" y="305" width="160" height="55" fill="#1e40af" stroke="#93c5fd" stroke-width="2" rx="6" stroke-dasharray="5 3"/>
  <text x="110" y="328" fill="#dbeafe" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">Hermes3D-worktrees</text>
  <text x="110" y="343" fill="#bfdbfe" font-family="sans-serif" font-size="9" text-anchor="middle">umbrella dir (NOT a repo)</text>
  <text x="110" y="354" fill="#bfdbfe" font-family="sans-serif" font-size="9" text-anchor="middle">→ lm-studio-default sub-worktree</text>

  <!-- Hermes3D-OS (independent, bottom-right) -->
  <rect x="410" y="305" width="160" height="55" fill="#7c2d12" stroke="#fdba74" stroke-width="2" rx="6"/>
  <text x="490" y="328" fill="#fed7aa" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">Hermes3D-OS</text>
  <text x="490" y="343" fill="#fed7aa" font-family="sans-serif" font-size="9" text-anchor="middle">SEPARATE remote</text>
  <text x="490" y="354" fill="#fed7aa" font-family="sans-serif" font-size="9" text-anchor="middle">apps/web + apps/api</text>

  <!-- Edges -->
  <!-- Hermes3D ↔ handoffs (worktree) -->
  <line x1="225" y1="190" x2="190" y2="80" stroke="#f472b6" stroke-width="2"/>
  <text x="170" y="140" fill="#fbcfe8" font-family="sans-serif" font-size="10">worktree (.git share)</text>

  <!-- Hermes3D ↔ h3d-gui (sibling clone, dashed) -->
  <line x1="375" y1="190" x2="410" y2="80" stroke="#6ee7b7" stroke-width="2" stroke-dasharray="5 3"/>
  <text x="395" y="140" fill="#a7f3d0" font-family="sans-serif" font-size="10">sibling clone</text>

  <!-- Hermes3D ↔ worktrees umbrella -->
  <line x1="225" y1="210" x2="190" y2="320" stroke="#93c5fd" stroke-width="2"/>
  <text x="115" y="258" fill="#bfdbfe" font-family="sans-serif" font-size="10">worktrees → .git</text>

  <!-- Hermes3D ↔ Hermes3D-OS (consumes via bridge, dotted) -->
  <line x1="375" y1="210" x2="410" y2="320" stroke="#fdba74" stroke-width="2" stroke-dasharray="2 4"/>
  <text x="385" y="258" fill="#fed7aa" font-family="sans-serif" font-size="10">hermes_bridge.py</text>

  <!-- handoffs → h3d-gui (briefs flow) -->
  <line x1="190" y1="65" x2="410" y2="65" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="2 3" opacity="0.6"/>
  <text x="265" y="55" fill="#cbd5e1" font-family="sans-serif" font-size="9">briefs → audit</text>

  <!-- worktrees → Hermes3D-OS (LM Studio chain consumed by apps/api) -->
  <line x1="190" y1="335" x2="410" y2="335" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="2 3" opacity="0.6"/>
  <text x="240" y="325" fill="#cbd5e1" font-family="sans-serif" font-size="9">ADR-015 LM Studio → consumed by apps/api</text>

  <!-- Title -->
  <text x="300" y="20" fill="#f1f5f9" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">Hermes3D OS — 5 core repos topology</text>
  <text x="300" y="395" fill="#94a3b8" font-family="sans-serif" font-size="9" text-anchor="middle">solid = direct git tie · dashed = sibling clone or umbrella · dotted = runtime data path</text>
</svg>
