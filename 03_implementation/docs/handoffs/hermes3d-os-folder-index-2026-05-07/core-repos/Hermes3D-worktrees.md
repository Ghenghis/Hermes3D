# Hermes3D-worktrees

## Role in H3D OS

`G:\Github\Hermes3D-worktrees` is an **umbrella directory** holding additional `git worktree` checkouts of the canonical `Hermes3D` repo. It is NOT itself a repository — `git status` at the directory root errors with "not a git repository". It exists as an organizational holder so that multiple branches of `Hermes3D` can be checked out simultaneously without polluting the main `Hermes3D` working tree.

As of 2026-05-07 it contains a single sub-worktree, `lm-studio-default/`, which is checked out on branch `feat/cp-h3d-lm-studio-default` and represents the LM Studio default + Ollama fallback + Hipfire optional integration line (ADR-015). This is where the Hermes3D OS's local-LLM provider chain experiment lives.

The directory was created on 2026-05-03, suggesting it was set up as part of the secrets-backup / overnight-Codex-queue work. Future worktrees (e.g., for the `claude/folder-index-2026-05-07` lane) could be added here, though that lane is currently in `_claude_worktrees/` instead.

## Recent activity

Top-level (umbrella): no git history (not a repo).

Sub-worktree `lm-studio-default/` (branch `feat/cp-h3d-lm-studio-default`):

```
1c6eeab test(bridge): relax provider-health assertion for ADR-015 chain
0be0b9f feat: LM Studio default + Ollama fallback + Hipfire optional (ADR-015)
3fde207 docs(release): draft v5.3.0 release notes
a39cbf8 docs(readme): v2 marketing rewrite + Mermaid + theme-aware SVG + truth-gate accordion
5b11f6c 2026-05-03 docs(adr): ADR-014 — audit of blender-mcp-native (verdict: REJECT)
c3e68d1 2026-05-03 docs(handoff): overnight Codex queue — 1 master + 6 task briefs + roadmap
b767100 2026-05-03 feat(backup): local-only secrets backup — Syncthing + Restic-B2 scripts
```

(Top three commits are from this branch; remainder are inherited from `chore/exclude-apps-folder` ancestor.)

## Branches

Umbrella: N/A.

Sub-worktree `lm-studio-default/`:
- Local: `feat/cp-h3d-lm-studio-default` (HEAD)
- Inherits all remote branches of canonical `Hermes3D` via shared `.git`

Remote (sub-worktree): `origin = https://github.com/Ghenghis/Hermes3D.git`

## Key directories (deep tree)

- `Hermes3D-worktrees/` (umbrella)
  - `lm-studio-default/` — sub-worktree with full Hermes3D 7-folder layout
    - `00_overview/` … `06_release/`
    - `agents/`, `env/`, `handoffs/`, `hermes3d_gui_contract_kit_v4.1/`, `schemas/`, `scripts/`, `site/`, `var/`
    - `CONTRIBUTING.md`, `HERMES3D_DELIVERY_README.md`, `Hermes3D-OS.md`, `README.md`
    - `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `run.bat`

## Key files

| File | Purpose |
| --- | --- |
| `lm-studio-default/README.md` | v2 marketing rewrite (theme-aware SVG, Mermaid, accordion) |
| `lm-studio-default/CONTRIBUTING.md` | Contributor guide |
| `lm-studio-default/HERMES3D_DELIVERY_README.md` | Delivery contract |
| `lm-studio-default/Hermes3D-OS.md` | OS surface (same as canonical) |
| `lm-studio-default/pyproject.toml` | hermes3d-os-lite v5.0.0 |
| `lm-studio-default/06_release/` | v5.3.0 release notes draft |
| `lm-studio-default/02_architecture/` | ADR-015 LM Studio chain spec (target location) |
| `lm-studio-default/03_implementation/` | LM Studio adapter + Ollama fallback impl |
| `lm-studio-default/handoffs/` | LM-Studio-specific handoff briefs |
| `lm-studio-default/run.bat` | Local launcher |

## Relationships to other H3D repos

- **Sub-worktree of `Hermes3D`** — the `.git` file inside `lm-studio-default/` points back into `G:\Github\Hermes3D\.git\worktrees\lm-studio-default`. Branch operations propagate to the canonical repo.
- Independent of `h3d-gui-wiring-codex` (which is a sibling clone, not a worktree share).
- Independent of `Hermes3D-OS` (different remote).
- `Hermes3D-handoffs` is a sibling worktree of the same canonical repo.
- ADR-015 LM Studio work targets the local-LLM provider chain that `Hermes3D-OS/apps/api/services/` will eventually consume via `hermes_bridge.py`.

## Status

**ACTIVE (single worktree)** — umbrella directory live since 2026-05-03; `lm-studio-default` sub-worktree is the only active member. Branch `feat/cp-h3d-lm-studio-default` is ahead of `chore/exclude-apps-folder` by ADR-015 commits but has not yet merged to `develop`.

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b1020"/>
  <rect x="170" y="20" width="160" height="50" fill="#1e3a8a" stroke="#60a5fa" stroke-width="2" rx="6"/>
  <text x="250" y="40" fill="#e0e7ff" font-family="sans-serif" font-size="13" text-anchor="middle" font-weight="bold">Hermes3D</text>
  <text x="250" y="58" fill="#a5b4fc" font-family="sans-serif" font-size="9" text-anchor="middle">canonical repo (.git)</text>
  <rect x="150" y="120" width="200" height="40" fill="#1e40af" stroke="#93c5fd" stroke-width="1.5" rx="5" stroke-dasharray="4 2"/>
  <text x="250" y="142" fill="#dbeafe" font-family="sans-serif" font-size="11" text-anchor="middle" font-weight="bold">Hermes3D-worktrees/</text>
  <text x="250" y="155" fill="#bfdbfe" font-family="sans-serif" font-size="9" text-anchor="middle">umbrella (NOT a repo)</text>
  <rect x="180" y="210" width="140" height="50" fill="#3b0764" stroke="#c084fc" stroke-width="1.5" rx="5"/>
  <text x="250" y="230" fill="#e9d5ff" font-family="sans-serif" font-size="11" text-anchor="middle" font-weight="bold">lm-studio-default</text>
  <text x="250" y="245" fill="#e9d5ff" font-family="sans-serif" font-size="9" text-anchor="middle">feat/cp-h3d-lm-studio-default</text>
  <text x="250" y="256" fill="#e9d5ff" font-family="sans-serif" font-size="8" text-anchor="middle">ADR-015</text>
  <line x1="250" y1="70" x2="250" y2="120" stroke="#60a5fa" stroke-width="2"/>
  <text x="260" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9">organizes</text>
  <line x1="250" y1="160" x2="250" y2="210" stroke="#c084fc" stroke-width="2"/>
  <text x="260" y="188" fill="#cbd5e1" font-family="sans-serif" font-size="9">contains</text>
  <line x1="320" y1="225" x2="380" y2="50" stroke="#60a5fa" stroke-width="1" stroke-dasharray="3 3" opacity="0.7"/>
  <text x="360" y="160" fill="#a5b4fc" font-family="sans-serif" font-size="9">.git → Hermes3D/.git/worktrees/</text>
</svg>
