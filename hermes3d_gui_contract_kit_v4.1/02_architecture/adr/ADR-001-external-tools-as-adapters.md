# ADR-001: External Tools as Adapters, Not Vendored Core

## Decision
Hermes3D will integrate Blender, slicers, Printrun, Moonraker, Fluidd, Mainsail, and OctoPrint through adapters rather than merging those codebases into Hermes3D core.

## Rationale
Large upstream tools have their own release cycles, dependencies, and GUIs. Hermes3D should orchestrate, not fork them.

## Consequences
- Easier updates.
- Safer rollback.
- Cleaner UI.
- Better proof gating.
- Less risk from upstream changes.
