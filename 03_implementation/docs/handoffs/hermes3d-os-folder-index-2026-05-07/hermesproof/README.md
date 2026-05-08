# HermesProof folder index (2026-05-07)

Index of the six top-level `hermesproof-*` folders under `G:\Github\`.

The folders model the four stages of the HermesProof pipeline:

```
TRIGGER  →  WIZARD-GATES  →  QUEUE  →  NEXT-TASK (consumer)
```

All six folders are **sandboxes / placeholders** as of 2026-05-07. Only `hermesproof-trigger-sandbox` contains a captured runtime state (rich enough to serve as the canonical fixture for the proof shape). The rest are README-only or empty.

## Folder summary

| Folder                              | Stage    | Status                            | Notes                                                              |
|-------------------------------------|----------|-----------------------------------|--------------------------------------------------------------------|
| [hermesproof-trigger-sandbox](./hermesproof-trigger-sandbox.md) | TRIGGER  | SANDBOX (rich fixture)            | Real `.hermes3d_orchestrator/` capture: tasks, gates, evidence ledger, handoffs |
| [hermesproof-wizard-gates](./hermesproof-wizard-gates.md)       | WIZARD   | SANDBOX (README-only)             | Placeholder for gate-allowlist + wizard UI                         |
| [hermesproof-wizard-sandbox](./hermesproof-wizard-sandbox.md)   | WIZARD   | ARCHIVED (empty, no `.git`)       | Abandoned scratch                                                  |
| [hermesproof-queue-sandbox](./hermesproof-queue-sandbox.md)     | QUEUE    | SANDBOX (README + untracked stub) | Unversioned baseline producer                                      |
| [hermesproof-queue-sandbox-v05](./hermesproof-queue-sandbox-v05.md) | QUEUE | SANDBOX (README-only)            | v0.5 protocol-break experiment placeholder                         |
| [hermesproof-queue-next-task](./hermesproof-queue-next-task.md) | QUEUE-CONSUMER | SANDBOX (README + untracked stub) | Drains the queue; pairs with `hermes_pick_task` MCP tool         |

## Truth-gate / proof-gate shape (canonical, from trigger-sandbox)

The trigger-sandbox capture is what the rest of the pipeline is meant to consume:

- `tasks/<id>.json` — claim record with `status`, `claimed_utc`, `heartbeat_utc`, `files[]`.
- `evidence/released_<lockid>_<ms>.json` — per-lock packet with `acquired_utc`, `expires_utc`, immutable `history[]` (acquired -> heartbeat -> released).
- `gates/gate_<id>_<ms>.json` — gate-run record with allowlisted `command`/`args`, `exit_code`, `duration_ms`, `stdout_tail`, `stderr_tail`, `ok`.
- `evidence/ledger.ndjson` — append-only NDJSON, every entry signs the prior via `prev_hash` -> `entry_hash` (sha256 chain).
- `handoffs/handoff_<id>.json` — requester/owner/decision_note for ownership transfer between roles.
- `events.ndjson` — flat event-bus tail of every state change.

A proof = `(task, locks-evidence, gates-passed, ledger-tail-with-matching-hash)`.

## Master pipeline diagram (~700x400)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="700" height="400" font-family="system-ui,sans-serif" font-size="11">
  <rect width="700" height="400" fill="#fafafa"/>
  <text x="350" y="22" text-anchor="middle" font-size="15" font-weight="bold">HermesProof pipeline (G:\Github\hermesproof-*)</text>
  <text x="350" y="40" text-anchor="middle" font-size="10" fill="#666">trigger -> wizard-gates -> queue -> next-task -> worker</text>

  <!-- Stage 1: TRIGGER -->
  <rect x="20" y="70" width="140" height="80" fill="#e6f0ff" stroke="#3b6cb5" stroke-width="2"/>
  <text x="90" y="92" text-anchor="middle" font-weight="bold">TRIGGER</text>
  <text x="90" y="110" text-anchor="middle" font-size="10">trigger-sandbox</text>
  <text x="90" y="125" text-anchor="middle" font-size="9" fill="#444">claim_task + lock_files</text>
  <text x="90" y="138" text-anchor="middle" font-size="9" fill="#444">contracts/CP-UX-A_*</text>

  <!-- Stage 2: WIZARD-GATES -->
  <rect x="200" y="70" width="140" height="80" fill="#fff2cc" stroke="#b58c2a" stroke-width="2"/>
  <text x="270" y="92" text-anchor="middle" font-weight="bold">WIZARD-GATES</text>
  <text x="270" y="110" text-anchor="middle" font-size="10">wizard-gates</text>
  <text x="270" y="125" text-anchor="middle" font-size="9" fill="#444">run_gate (allowlist)</text>
  <text x="270" y="138" text-anchor="middle" font-size="9" fill="#444">gates/gate_*.json</text>

  <!-- Stage 3: QUEUE -->
  <rect x="380" y="70" width="140" height="80" fill="#ffe6e6" stroke="#a33" stroke-width="2"/>
  <text x="450" y="92" text-anchor="middle" font-weight="bold">QUEUE</text>
  <text x="450" y="110" text-anchor="middle" font-size="10">queue-sandbox</text>
  <text x="450" y="125" text-anchor="middle" font-size="9" fill="#444">queue-sandbox-v05</text>
  <text x="450" y="138" text-anchor="middle" font-size="9" fill="#444">emit_event + ledger</text>

  <!-- Stage 4: NEXT-TASK -->
  <rect x="540" y="70" width="140" height="80" fill="#e6ffe6" stroke="#2e8b57" stroke-width="2"/>
  <text x="610" y="92" text-anchor="middle" font-weight="bold">NEXT-TASK</text>
  <text x="610" y="110" text-anchor="middle" font-size="10">queue-next-task</text>
  <text x="610" y="125" text-anchor="middle" font-size="9" fill="#444">pick_task</text>
  <text x="610" y="138" text-anchor="middle" font-size="9" fill="#444">dispatch_recommend</text>

  <!-- Arrows top row -->
  <line x1="160" y1="110" x2="200" y2="110" stroke="#333" stroke-width="2" marker-end="url(#a)"/>
  <line x1="340" y1="110" x2="380" y2="110" stroke="#333" stroke-width="2" marker-end="url(#a)"/>
  <line x1="520" y1="110" x2="540" y2="110" stroke="#333" stroke-width="2" marker-end="url(#a)"/>

  <!-- Evidence ledger (durable proof spine) -->
  <rect x="100" y="200" width="500" height="60" fill="#f0e6ff" stroke="#5b3bb5" stroke-width="2"/>
  <text x="350" y="220" text-anchor="middle" font-weight="bold">evidence/ledger.ndjson  (hash-chained)</text>
  <text x="350" y="237" text-anchor="middle" font-size="10">prev_entry_id -> prev_hash -> entry_hash    (sha256)</text>
  <text x="350" y="252" text-anchor="middle" font-size="9" fill="#666">every stage appends; tamper anywhere breaks the chain</text>

  <!-- Lines from each stage to ledger -->
  <line x1="90" y1="150" x2="180" y2="200" stroke="#5b3bb5" stroke-dasharray="3 3"/>
  <line x1="270" y1="150" x2="300" y2="200" stroke="#5b3bb5" stroke-dasharray="3 3"/>
  <line x1="450" y1="150" x2="430" y2="200" stroke="#5b3bb5" stroke-dasharray="3 3"/>
  <line x1="610" y1="150" x2="550" y2="200" stroke="#5b3bb5" stroke-dasharray="3 3"/>

  <!-- Worker -->
  <rect x="280" y="300" width="140" height="50" fill="#e6f0ff" stroke="#3b6cb5" stroke-width="2"/>
  <text x="350" y="322" text-anchor="middle" font-weight="bold">worker</text>
  <text x="350" y="338" text-anchor="middle" font-size="9">claim + lock + edit + release</text>
  <line x1="610" y1="150" x2="420" y2="300" stroke="#333" stroke-width="2" marker-end="url(#a)"/>

  <!-- Status legend -->
  <rect x="20" y="370" width="10" height="10" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="36" y="380" font-size="9">SANDBOX (real fixture)</text>
  <rect x="170" y="370" width="10" height="10" fill="#fff2cc" stroke="#b58c2a"/>
  <text x="186" y="380" font-size="9">SANDBOX (README only)</text>
  <rect x="320" y="370" width="10" height="10" fill="#ffe6e6" stroke="#a33"/>
  <text x="336" y="380" font-size="9">SANDBOX (untracked stub)</text>
  <rect x="470" y="370" width="10" height="10" fill="#e6ffe6" stroke="#2e8b57"/>
  <text x="486" y="380" font-size="9">SANDBOX (consumer)</text>
  <rect x="600" y="370" width="10" height="10" fill="#f0e6ff" stroke="#5b3bb5"/>
  <text x="616" y="380" font-size="9">durable proof</text>

  <defs>
    <marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
  </defs>
</svg>
```

## Cross-references

- Source: `G:\Github\hermesproof-*`
- Index dir: `G:\Github\_claude_worktrees\h3d-folder-index\03_implementation\docs\handoffs\hermes3d-os-folder-index-2026-05-07\hermesproof\`
- Canonical fixture: `G:\Github\hermesproof-trigger-sandbox\.hermes3d_orchestrator\` (untracked)
- Related: hermes3d-mcp-lock-orchestrator (the tool family backing these sandboxes)
