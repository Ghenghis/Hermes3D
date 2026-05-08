# hermesproof-queue-next-task

**Component**: QUEUE (consumer)
**Status**: SANDBOX (init commit + untracked orchestrator state dir)
**Branch**: `main`
**Last commit**: `e277e4a init` (2026-05-02)

## Purpose

`hermesproof-queue-next-task` is the consumer-side of the HermesProof queue: the worker that pulls the next ready proof/task off the queue and dispatches it. It pairs with the producer-side `hermesproof-queue-sandbox*` folders. The folder has been bootstrapped with a `.hermes3d_orchestrator/` runtime directory (untracked), suggesting someone exercised the orchestrator MCP locally to draft what "next-task" semantics look like before lifting the protocol up to a real package.

In the broader HermesProof flow, this is where `hermes_pick_task` / `hermes_dispatch_recommend` MCP tools would land their decision: read pending tasks, sort by gates-passed + priority, claim, hand off to the worker that owns the matching files.

## Branch & last commit

- Branch: `main`
- Working tree: untracked `.hermes3d_orchestrator/` directory
- Commit: `e277e4a init`

## Key files / artifacts

| Path                          | Notes                                            |
|-------------------------------|--------------------------------------------------|
| `README.md`                   | One line: `# Next task sandbox`                  |
| `.hermes3d_orchestrator/`     | Untracked orchestrator state stub                |
| `.git/`                       | Single-commit history                            |

No `package.json`, no source files, no truth-gate config.

## Truth-gate / proof-gate flow

Not yet implemented as code in this folder, but the consumer protocol is implied:

1. `hermes_list_pending_tasks` returns ready tasks with passing gates.
2. `hermes_dispatch_recommend` ranks them.
3. Worker calls `hermes_claim_task`, then `hermes_lock_files`.
4. Evidence updates flow through `hermes_append_evidence` and `hermes_run_gate`.
5. On success: `hermes_record_outcome` + `hermes_release_files` + `hermes_release_task`.

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300" font-family="system-ui,sans-serif" font-size="12">
  <rect width="500" height="300" fill="#fafafa"/>
  <text x="250" y="22" text-anchor="middle" font-size="14" font-weight="bold">hermesproof-queue-next-task (consumer)</text>
  <rect x="20" y="100" width="120" height="60" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="80" y="125" text-anchor="middle">queue-sandbox</text>
  <text x="80" y="142" text-anchor="middle" font-size="10">producer / FIFO</text>
  <rect x="180" y="100" width="140" height="60" fill="#ffe6e6" stroke="#a33"/>
  <text x="250" y="122" text-anchor="middle" font-weight="bold">queue-next-task</text>
  <text x="250" y="140" text-anchor="middle" font-size="10">hermes_pick_task</text>
  <text x="250" y="154" text-anchor="middle" font-size="10">+ dispatch_recommend</text>
  <rect x="360" y="100" width="120" height="60" fill="#e6ffe6" stroke="#2e8b57"/>
  <text x="420" y="125" text-anchor="middle">worker</text>
  <text x="420" y="142" text-anchor="middle" font-size="10">claim+lock+work</text>
  <line x1="140" y1="130" x2="180" y2="130" stroke="#333" marker-end="url(#a)"/>
  <line x1="320" y1="130" x2="360" y2="130" stroke="#333" marker-end="url(#a)"/>
  <rect x="180" y="200" width="140" height="50" fill="#f5f5f5" stroke="#888" stroke-dasharray="3 3"/>
  <text x="250" y="222" text-anchor="middle" font-size="10">.hermes3d_orchestrator/</text>
  <text x="250" y="238" text-anchor="middle" font-size="10">(untracked stub)</text>
  <line x1="250" y1="160" x2="250" y2="200" stroke="#333" stroke-dasharray="3 3"/>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#333"/></marker></defs>
</svg>
```
