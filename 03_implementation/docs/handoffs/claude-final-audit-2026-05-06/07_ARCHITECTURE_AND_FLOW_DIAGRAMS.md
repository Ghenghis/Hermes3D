# Architecture and Flow Diagrams

Generated: 2026-05-07T01:03 UTC

---

## PR Merge Flow

```mermaid
flowchart LR
  A["Step 0: PR #80\nTS7026 CI fix"] --> B["Tier 1\n#53 #54 #55 #56 #57\n#58 #59 #60 #61 #62\n#63 #65 #67 #68 #70"]
  B --> C["Tier 2\n#66 first\n(source-ui app.py router)"]
  C --> D["#69 second\n(settings router — UNION\nkeep both routers)"]
  D --> E["Tier 3\n#64 first\n(voice adapters)"]
  E --> F["#71 second\n(printers adapters — UNION\nkeep all methods)"]
  F --> G["Tier 4\n#72 final integrator"]
  G --> H["Audit PRs\n#74 #75 #76 #77 #78 #79"]
  H --> I["Global gates\nnpm run lint\npy_compile\nscan_active_ui_no_fake.py"]
  I --> J["Codex continues\nremaining implementation\n(#73 code-operator + beyond)"]
```

---

## Hermes Agent Code Workflow (MCP Lock Protocol)

```mermaid
flowchart TD
  I["Intent stated in chat"] --> T["hermes_a2a_create_task\n(submit task)"]
  T --> C["hermes_claim_task\n(mark working)"]
  C --> L["hermes_lock_files\n(atomic lock — rolls back if any\nfile locked by other owner)"]
  L --> HB["hermes_heartbeat\n(refresh every ~10 min)"]
  HB --> SN["Pre-snapshot\n(git diff HEAD for rollback ref)"]
  SN --> P["Edit files\n(only files under lock)"]
  P --> G["hermes_run_gate\n(allowlisted: tsc, pytest, py_compile)"]
  G -->|pass| E["hermes_append_evidence\n(hash-chained entry)"]
  G -->|fail| FIX["Fix failure\n(re-edit, re-gate)"]
  FIX --> G
  E --> RF["hermes_release_files\n(unlock owned files)"]
  RF --> RT["hermes_release_task\n(close task)"]
```

**No source changes without an active same-owner lock. No locks held after work is done.**

---

## Source OS Runtime Verification Flow

```mermaid
flowchart TD
  UI["Source OS Tab\n(60 app rows)"] --> API["GET /api/modules"]
  API --> DB["Module registry\n(SQLite or TOML)"]
  DB --> PROBE["Runtime probe\n(per app type)"]
  PROBE --> CLI["CLI binary probe\nsubprocess.run binary --version\nshell=False, allowlisted"]
  PROBE --> HTTP["HTTP probe\nrequests.get service_url timeout=2"]
  PROBE --> PY["Python import probe\nimportlib.util.find_spec module"]
  CLI --> STATUS["Status: installed / not_found / unknown"]
  HTTP --> STATUS
  PY --> STATUS
  STATUS --> BADGE["UI badge\ninstalled / source / ready / unknown / blocked"]
  BADGE --> GAP["UNKNOWN badge?\nDocument in ROADMAP\nnot a code bug"]
```

---

## Printer Safety Decision Flow

```mermaid
flowchart TD
  REQ["Physical action request\n(print / upload / move)"] --> S1CHECK["IP in CAMERA_ONLY_IPS?\n(S1: 192.168.0.12)"]
  S1CHECK -->|yes| BLOCK403["HTTP 403\nS1 is camera-only\nNo network side effect"]
  S1CHECK -->|no| POLICY["Policy gate\nIs action in agent allow-list?"]
  POLICY -->|fail| BLOCK403B["HTTP 403\nAction not permitted\nfor this agent role"]
  POLICY -->|pass| PROBE["Moonraker probe\nIs printer IDLE?"]
  PROBE -->|not idle| BLOCK409["HTTP 409\nPrinter not idle\nJob in progress"]
  PROBE -->|idle| JOB["Job context check\nValid job_id with proof artifact?"]
  JOB -->|no job| BLOCK400["HTTP 400\nNo active job context"]
  JOB -->|valid job| ACTION["Execute action\nRecord proof event\nAppend evidence"]
```

---

## Codex Takeover Flow

```mermaid
flowchart TD
  C["Claude stops\n(this handoff)"] --> READ["Codex reads\n00_EXECUTIVE_TAKEOVER_SUMMARY.md"]
  READ --> PR80["Confirm PR #80 CI green\n(TS7026 fix)"]
  PR80 --> MERGE0["gh pr merge 80 --squash"]
  MERGE0 --> TIER1["Merge Tier 1\n15 no-conflict PRs"]
  TIER1 --> TIER2["Merge Tier 2\n#66 then #69\n(UNION app.py)"]
  TIER2 --> TIER3["Merge Tier 3\n#64 then #71\n(UNION adapters)"]
  TIER3 --> TIER4["Merge Tier 4\n#72 final integrator"]
  TIER4 --> AUDIT["Merge audit PRs\n#74–#79"]
  AUDIT --> GATES["Run global gates\nlint + build + no-fake scan"]
  GATES -->|all pass| CODEX73["Codex merges #73\n(code-operator)"]
  CODEX73 --> IMPL["Continue remaining\nCodex implementation\n(beyond 20-lane scope)"]
```

---

## Hermes3D OS Tab Wiring Summary

```mermaid
graph LR
  subgraph "Completed Tabs (Claude lanes)"
    A[Source OS #66] --> BE[Backend API]
    B[Autopilot #62] --> BE
    C[Design #65] --> BE
    D[3D Generation #70] --> BE
    E[Jobs #68] --> BE
    F[Printers #71] --> BE
    G[Observe #67] --> BE
    H[Voice #64] --> BE
    I[Learning #62] --> BE
    J[Artifacts #61] --> BE
    K[Settings #69] --> BE
    L[Plugins #69] --> BE
    M[App Shell #54] --> BE
  end
  subgraph "Codex-Owned (pending)"
    N[Agents tab #73]
    O[Dashboard codex-master]
    P[Roadmap codex-master]
  end
  BE --> REAL["Real backend routes\nNo mock/fake data"]
```
