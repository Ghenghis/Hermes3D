# hermesproof-queue-sandbox

**Component**: QUEUE (producer / unversioned baseline)
**Status**: SANDBOX (init commit + untracked orchestrator state dir)
**Branch**: `main`
**Last commit**: `c2a295d init` (2026-05-02)

## Purpose

`hermesproof-queue-sandbox` is the unversioned baseline of the HermesProof QUEUE. It is the producer-side scratch space where freshly-passed proofs are enqueued, awaiting drain by `hermesproof-queue-next-task`. In the family it sits alongside `hermesproof-queue-sandbox-v05` (a versioned variant suggesting protocol-break experiments) and `hermesproof-queue-next-task` (the consumer). The folder hosts a one-line README and an untracked `.hermes3d_orchestrator/` stub showing someone exercised the orchestrator locally before any real protocol code landed.

This folder represents the canonical / unversioned naming for the queue protocol — the spec-stable baseline against which v0.5 (and any future versions) are compared.

## Branch & last commit

- Branch: `main`
- Working tree: untracked `.hermes3d_orchestrator/` directory
- Commit: `c2a295d init`

## Key files / artifacts

| Path                          | Notes                                |
|-------------------------------|--------------------------------------|
| `README.md`                   | One line: `# Queue sandbox`          |
| `.hermes3d_orchestrator/`     | Untracked orchestrator state stub    |
| `.git/`                       | Single-commit history                |

No `package.json`, no source files, no truth-gate config.

## Truth-gate / proof-gate flow

Not yet implemented. Intended producer protocol:

1. `wizard-gates` finishes its allowlisted gate suite via `hermes_run_gate`.
2. Producer calls `hermes_emit_event` with `kind=evidence-ready`.
3. Orchestrator appends to evidence ledger (hash-chained NDJSON, see trigger-sandbox).
4. Task transitions to `pending` for the next-task consumer.

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300" font-family="system-ui,sans-serif" font-size="12">
  <rect width="500" height="300" fill="#fafafa"/>
  <text x="250" y="22" text-anchor="middle" font-size="14" font-weight="bold">hermesproof-queue-sandbox (producer)</text>
  <rect x="20" y="100" width="120" height="60" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="80" y="125" text-anchor="middle">wizard-gates</text>
  <text x="80" y="142" text-anchor="middle" font-size="10">gates pass</text>
  <rect x="180" y="100" width="140" height="60" fill="#fff2cc" stroke="#b58c2a"/>
  <text x="250" y="122" text-anchor="middle" font-weight="bold">queue-sandbox</text>
  <text x="250" y="140" text-anchor="middle" font-size="10">enqueue evidence</text>
  <text x="250" y="154" text-anchor="middle" font-size="10">hermes_emit_event</text>
  <rect x="360" y="100" width="120" height="60" fill="#e6ffe6" stroke="#2e8b57"/>
  <text x="420" y="125" text-anchor="middle">queue-next-task</text>
  <text x="420" y="142" text-anchor="middle" font-size="10">consumer</text>
  <line x1="140" y1="130" x2="180" y2="130" stroke="#333" marker-end="url(#a)"/>
  <line x1="320" y1="130" x2="360" y2="130" stroke="#333" marker-end="url(#a)"/>
  <rect x="180" y="200" width="140" height="50" fill="#f5f5f5" stroke="#888" stroke-dasharray="3 3"/>
  <text x="250" y="222" text-anchor="middle" font-size="10">.hermes3d_orchestrator/</text>
  <text x="250" y="238" text-anchor="middle" font-size="10">(untracked stub)</text>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#333"/></marker></defs>
</svg>
```
