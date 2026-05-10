# Exclusions — Folders Intentionally NOT Indexed

Generated: 2026-05-07

This document lists every folder under `G:\Github\` that fell within the date filter (2026-04-27 → 2026-05-07) but was **excluded** from the Hermes3D OS folder index, and the reason for each exclusion.

The user's instruction was explicit: *"only include for hermes3d os; exclude any folders that don't reflect Hermes3d os."*

---

## Excluded Folders

| Folder | LastWriteTime | Reason for exclusion |
|---|---|---|
| `kilocode-Azure2` | 2026-05-04 15:13 | **Not Hermes3D**. Separate `kilocode` project on Azure. |
| `contract-kit-v17` | 2026-05-04 14:51 | **Not Hermes3D**. The `Hermes3D-GUI-Wiring-Contract-Kit/` lives *inside* `Hermes3D` (and is referenced by `source-os-60-apps/REGISTRY.md`). The top-level `contract-kit-v17` is a different, unrelated artifact toolkit. |
| `contract-kit-v17-purge-034406` | 2026-04-28 03:44 | **Not Hermes3D**. Purge variant of the unrelated `contract-kit-v17`. |
| `contract-kit-v17-backup-20260427-211327.git` | 2026-04-27 21:13 | **Not Hermes3D**. Bare-git backup of the unrelated `contract-kit-v17`. |
| `_repo_rescue_evidence` | 2026-04-27 14:22 | **Generic recovery artifact**. Not specifically Hermes3D OS work; would be relevant if a corruption incident is being audited but not for the active OS index. |
| `TRELLIS.2` | 2026-04-29 13:55 | **Vendored AI model, not H3D infrastructure**. TRELLIS is one of the 60 registered Source OS apps (`three_d_generation_trellis2`), but this top-level folder is a separate full clone of the upstream model repo, not part of the OS workflow. The `h3dos-codex-triposr/` lane is the one that integrates a sibling 3D-gen model. The Source OS registry entry covers the integration story. |
| `Agentic-Modeler` | 2026-04-29 14:10 | **Separate project**. Not visibly connected to Hermes3D OS in the date window. May be an exploratory side project. |

**Total excluded**: 7 folders.

---

## Exclusion Reasoning Pattern

Three exclusion rules were applied:

1. **Different product line** (`kilocode-Azure2`, `Agentic-Modeler`)
2. **Generic infrastructure shared across many projects** (`_repo_rescue_evidence`, `contract-kit-v17*`)
3. **Vendored upstream where the integration story already lives in another folder** (`TRELLIS.2` — the integration is captured in `h3dos-codex-triposr/` and the Source OS registry entry)

---

## What If You Disagree?

If any excluded folder turns out to be Hermes3D-relevant, the procedure to add it back is:

1. Decide which category it belongs to (use `01_TAXONOMY.md`).
2. Inspect the folder using the same template as the per-folder markdowns.
3. Add a `<folder-name>.md` to the appropriate category subdirectory.
4. Update the category README's inventory table.
5. Update the totals in `00_INDEX.md` and remove the folder from this exclusion list.

For ambiguous folders (the contract-kit family and TRELLIS in particular), inspect for direct imports of `hermes3d.*` packages or references to the Hermes Agent contract before reclassifying.

---

## Folders Outside the Date Window

The following folders exist in `G:\Github\` but were modified **before 2026-04-27** and are not included in this index regardless of relevance:

- Any older `Hermes3D-*` snapshots (e.g., from earlier sprints)
- Older Codex/Claude worktrees that have been pruned or stale
- Vendored apps that haven't been refreshed since before the date window

To extend the date range, change the filter in the maintenance procedure documented in `01_TAXONOMY.md`.

---

## Also Noted but Not Indexed

Two folders dated within the window contain Hermes3D content but are entirely covered by other categories' deeper inspection:

- `Hermes3D-OS/_claude_worktrees/` — visible only as a child of `Hermes3D-OS`. The `_claude_worktrees/` at the *top level* of `G:\Github\` is the canonical multi-worktree umbrella covered by `worktree-collections/_claude_worktrees.md`.

These are mentioned for completeness and are not exclusions per se — they are simply represented elsewhere.
