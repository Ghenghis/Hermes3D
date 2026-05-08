# hermesproof-wizard-sandbox

**Component**: WIZARD
**Status**: ARCHIVED (empty, not even a git repo)
**Branch**: n/a — not a git repository
**Last commit**: n/a

## Purpose

`hermesproof-wizard-sandbox` is the second WIZARD-side scratch folder in the HermesProof workspace family. It was presumably created to scratch out wizard-step UI flows (the human/agent-facing interaction layer that gates evidence emission). Unlike its sibling `hermesproof-wizard-gates` (which is a real one-commit git repo), this folder contains no `.git/` directory, no `README.md`, and no files at all — it is effectively an empty placeholder.

Given the absence of any history or content, treat this as an archived/abandoned scratch space. Any future wizard work should use `hermesproof-wizard-gates` (the gates-focused sibling) or be merged into the main Hermes3D repo.

## Branch & last commit

- Not under version control — `git -C` returns *fatal: not a git repository*.
- No commits, no branches, no remote.

## Key files / artifacts

The folder is empty. Listing returns only `./` and `../`.

## Truth-gate / proof-gate flow

None present. No code, no config, no evidence files. If reactivated, the natural pairing is with `hermesproof-wizard-gates` (provides the gate-allowlist) and `hermesproof-trigger-sandbox` (provides the live orchestrator state showing the gate-run protocol).

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300" font-family="system-ui,sans-serif" font-size="12">
  <rect width="500" height="300" fill="#fafafa"/>
  <text x="250" y="22" text-anchor="middle" font-size="14" font-weight="bold">hermesproof-wizard-sandbox (ARCHIVED / empty)</text>
  <rect x="170" y="80" width="160" height="80" fill="#f0f0f0" stroke="#999" stroke-dasharray="6 4"/>
  <text x="250" y="115" text-anchor="middle" font-weight="bold" fill="#666">empty folder</text>
  <text x="250" y="135" text-anchor="middle" font-size="10" fill="#666">no .git, no files</text>
  <text x="250" y="200" text-anchor="middle" font-size="11">Sibling active sandboxes:</text>
  <rect x="60" y="220" width="160" height="40" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="140" y="245" text-anchor="middle" font-size="11">hermesproof-wizard-gates</text>
  <rect x="280" y="220" width="160" height="40" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="360" y="245" text-anchor="middle" font-size="11">hermesproof-trigger-sandbox</text>
  <line x1="220" y1="160" x2="140" y2="220" stroke="#888" stroke-dasharray="3 3"/>
  <line x1="280" y1="160" x2="360" y2="220" stroke="#888" stroke-dasharray="3 3"/>
</svg>
```
