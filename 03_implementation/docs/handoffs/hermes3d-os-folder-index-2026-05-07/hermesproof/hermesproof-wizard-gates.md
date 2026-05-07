# hermesproof-wizard-gates

**Component**: WIZARD
**Status**: SANDBOX (empty placeholder, single `init` commit)
**Branch**: `main`
**Last commit**: `90a1a19 init` (2026-05-02)

## Purpose

`hermesproof-wizard-gates` is a placeholder sandbox reserved for the WIZARD-side of the HermesProof gate-execution flow. The wizard is the human-or-LLM-driven step that walks an agent through the proof-generation checklist (the "gates" that must pass before evidence may be queued and consumed). In production this folder would host the wizard UI/CLI and the gate-allowlist definitions that the orchestrator's `hermes_run_gate` MCP tool consults.

Currently the folder contains only a one-line README and no implementation; it appears reserved for a future split-out of wizard-gate logic from the larger HermesProof orchestrator. There is no `package.json`, no source, no truth-gate config — the directory exists to claim the name and the git history.

## Branch & last commit

- Branch: `main`
- Working tree: clean
- Commit: `90a1a19 init`

## Key files / artifacts

| Path                      | Notes                              |
|---------------------------|------------------------------------|
| `README.md`               | One line: `# Wizard gate sandbox`  |
| `.git/`                   | Single-commit history              |

No `package.json`, no source files, no truth-gate config, no proof artifacts.

## Truth-gate / proof-gate flow

Not yet implemented in this folder. The intended role (inferred from sibling sandboxes) is:

1. Wizard renders an ordered checklist of gates (e.g., `git-status`, `git-diff-check`, `tests.unit`).
2. For each gate, wizard invokes `hermes_run_gate` on the orchestrator MCP.
3. Gate result JSON (with `ok`, `exit_code`, `stdout_tail`) is appended to the orchestrator's `gates/` directory.
4. Once all required gates pass, the wizard signals readiness for queue handoff.

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300" font-family="system-ui,sans-serif" font-size="12">
  <rect width="500" height="300" fill="#fafafa"/>
  <text x="250" y="22" text-anchor="middle" font-size="14" font-weight="bold">hermesproof-wizard-gates (SANDBOX)</text>
  <rect x="20" y="60" width="120" height="60" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="80" y="85" text-anchor="middle">Agent / User</text>
  <text x="80" y="102" text-anchor="middle" font-size="10">starts proof</text>
  <rect x="180" y="60" width="140" height="60" fill="#fff2cc" stroke="#b58c2a" stroke-dasharray="4 3"/>
  <text x="250" y="82" text-anchor="middle" font-weight="bold">wizard-gates</text>
  <text x="250" y="100" text-anchor="middle" font-size="10">(placeholder)</text>
  <text x="250" y="114" text-anchor="middle" font-size="10">runs gate checklist</text>
  <rect x="360" y="60" width="120" height="60" fill="#e6ffe6" stroke="#2e8b57"/>
  <text x="420" y="82" text-anchor="middle">hermes_run_gate</text>
  <text x="420" y="100" text-anchor="middle" font-size="10">(MCP tool)</text>
  <line x1="140" y1="90" x2="180" y2="90" stroke="#333" marker-end="url(#a)"/>
  <line x1="320" y1="90" x2="360" y2="90" stroke="#333" marker-end="url(#a)"/>
  <rect x="180" y="170" width="140" height="60" fill="#f5f5f5" stroke="#888"/>
  <text x="250" y="195" text-anchor="middle">gates/*.json</text>
  <text x="250" y="212" text-anchor="middle" font-size="10">orchestrator state</text>
  <line x1="420" y1="120" x2="320" y2="170" stroke="#333" stroke-dasharray="3 3" marker-end="url(#a)"/>
  <text x="20" y="270" font-size="10">Status: empty sandbox; no impl yet.</text>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#333"/></marker></defs>
</svg>
```
