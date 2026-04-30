# ADR-003: UI-Final Does Not Block Stabilization

## Decision
UI-Final work happens on `feat/ui-final-dashboard` and must not disrupt rc1 stabilization.

## Rationale
The current release line needs green gates first. The polished dashboard is valuable but belongs to a separate proof-gated phase.

## Merge condition
UI-Final merges only after:
- rc1 is cut from green develop.
- UI-Final screenshot gate passes.
- Adapter tests pass in detect/read-only mode.
