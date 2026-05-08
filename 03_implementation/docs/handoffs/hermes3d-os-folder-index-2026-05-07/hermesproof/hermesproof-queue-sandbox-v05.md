# hermesproof-queue-sandbox-v05

**Component**: QUEUE
**Status**: SANDBOX (single `init` commit, README-only)
**Branch**: `main`
**Last commit**: `5e1dc59 init` (2026-05-02)

## Purpose

`hermesproof-queue-sandbox-v05` is a versioned (v0.5) placeholder folder for the QUEUE side of the HermesProof pipeline. The HermesProof "queue" is the durable handoff lane between gate-passing (proof produced) and consumer (proof verified / acted upon). This folder appears intended to capture a v0.5 snapshot of queue-protocol experiments (perhaps an A/B against the unversioned `hermesproof-queue-sandbox` sibling), but currently it holds only a one-line README and a single-commit git history.

There is no `package.json`, no source, no protocol definition file, and no orchestrator state. Treat it as a reserved name for queue-protocol versioning work that has not started.

## Branch & last commit

- Branch: `main`
- Working tree: clean
- Commit: `5e1dc59 init`

## Key files / artifacts

| Path        | Notes                            |
|-------------|----------------------------------|
| `README.md` | One line: `# Queue sandbox`      |
| `.git/`     | Single-commit history            |

## Truth-gate / proof-gate flow

Not yet implemented. The intended role (inferred from the surrounding HermesProof pipeline) is:

1. After `wizard-gates` reports all gates green, an evidence packet is enqueued.
2. The queue (this folder, v0.5) provides a FIFO with retry / dead-letter semantics.
3. `queue-next-task` (sibling) is the consumer that drains it.
4. Versioning (v0.5 here) suggests forthcoming protocol breaks vs. unversioned `hermesproof-queue-sandbox`.

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300" font-family="system-ui,sans-serif" font-size="12">
  <rect width="500" height="300" fill="#fafafa"/>
  <text x="250" y="22" text-anchor="middle" font-size="14" font-weight="bold">hermesproof-queue-sandbox-v05 (SANDBOX)</text>
  <rect x="20" y="120" width="110" height="60" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="75" y="145" text-anchor="middle">wizard-gates</text>
  <text x="75" y="162" text-anchor="middle" font-size="10">producer</text>
  <rect x="180" y="120" width="140" height="60" fill="#fff2cc" stroke="#b58c2a" stroke-dasharray="4 3"/>
  <text x="250" y="142" text-anchor="middle" font-weight="bold">queue-sandbox-v05</text>
  <text x="250" y="160" text-anchor="middle" font-size="10">(placeholder, v0.5)</text>
  <text x="250" y="174" text-anchor="middle" font-size="10">FIFO lane</text>
  <rect x="370" y="120" width="110" height="60" fill="#e6ffe6" stroke="#2e8b57"/>
  <text x="425" y="145" text-anchor="middle">queue-next-task</text>
  <text x="425" y="162" text-anchor="middle" font-size="10">consumer</text>
  <line x1="130" y1="150" x2="180" y2="150" stroke="#333" marker-end="url(#a)"/>
  <line x1="320" y1="150" x2="370" y2="150" stroke="#333" marker-end="url(#a)"/>
  <text x="20" y="245" font-size="10">v0.5 = forthcoming protocol break vs. unversioned hermesproof-queue-sandbox.</text>
  <text x="20" y="263" font-size="10">Status: empty placeholder; no impl yet.</text>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#333"/></marker></defs>
</svg>
```
