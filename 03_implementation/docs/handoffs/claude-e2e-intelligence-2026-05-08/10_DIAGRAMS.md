# 10 — Diagrams

Mermaid-only. The 6 required diagrams from the PR 104 contract.

---

## 1. GitHub Folder / Worktree Topology

```mermaid
graph TB
    subgraph CORE["Core Repos"]
        H3D[Hermes3D<br/>main repo<br/>30+ branches]
        H3DGUI[h3d-gui-wiring-codex<br/>chain runtime<br/>worktree of Hermes3D]
        H3DOS[Hermes3D-OS<br/>web SPA + API bridge<br/>independent repo]
        H3DHANDOFF[Hermes3D-handoffs<br/>frozen worktree<br/>cp5.1-c-handoff]
    end

    subgraph AGENT["Agent Infrastructure"]
        MCP[hermes3d-mcp-lock-orchestrator<br/>v0.7.0 PRIMARY<br/>44 MCP tools]
        BRIDGE[hp-hermes-agent-bridge<br/>v0.6.0 FALLBACK<br/>36 MCP tools]
        FRESH[hermes-agent-fresh<br/>NousResearch v0.12.0]
        ATOMIC[atomic-hermes<br/>AtomicBot fork]
        SANDBOX[hermes3d-mcp-test-sandbox<br/>CI fixture]
    end

    subgraph WORKTREES["Worktree Collections (49)"]
        CW[_claude_worktrees/<br/>29 sub-worktrees]
        CXW[_codex_worktrees/<br/>16 sub-worktrees]
        CXAW[_codex_audit_worktrees/<br/>4 sub-worktrees]
    end

    subgraph PROD["Active Lanes"]
        WIRE[h3dos-wire-tasks/<br/>18 single-button lanes]
        CXTASK[h3dos-codex-tasks/<br/>5 app integration]
        ENH[h3d-enhancements/<br/>7 enhancement branches]
    end

    subgraph APPS["Vendored Apps ~1.08 GB"]
        BLENDER[blender + blender-main]
        ORCA[OrcaSlicer-main]
        PRUSA[PrusaSlicer-master]
        PRINTRUN[Printrun-2.2.0]
        DESKTOP[hermes-desktop-main]
    end

    H3D --> H3DGUI
    H3D --> CW
    H3D --> CXW
    H3DGUI --> MCP
    H3DGUI --> WIRE
    H3DOS --> CXTASK
    MCP -.fallback.-> BRIDGE
    MCP -.references.-> FRESH
    MCP -.references.-> ATOMIC
    H3DGUI --> APPS
```

---

## 2. Hermes Agent E2E Coding Loop

```mermaid
flowchart TD
    START([User/Codex submits coding task]) --> LOAD[Load folder index]
    LOAD --> READY{e2e/readiness?}
    READY -- "BLOCKED 401"--> BLOCK0[STOP — Tier 0 user action<br/>replace MiniMax+DeepSeek keys<br/>in G:/private/.env]
    READY -- "ready=true" --> CLAIM[hermes_claim_task]
    CLAIM --> LOCK[hermes_lock_files]
    LOCK --> SNAP[hermes history/snapshots create]
    SNAP --> MINIMAX[MiniMax builder pass<br/>via /providers/smoke + chat]
    MINIMAX --> PROPOSE[Patch proposal artifact]
    PROPOSE --> DEEPSEEK[DeepSeek reviewer pass]
    DEEPSEEK --> REVIEW{Review accepts?}
    REVIEW -- "no" --> REPAIR[Repair plan<br/>no source mutation]
    REPAIR --> MINIMAX
    REVIEW -- "yes" --> APPLY[patch/apply-reviewed<br/>same-owner MCP lock]
    APPLY --> GATES[Run allowlisted gates<br/>git-diff-check + tests + lint]
    GATES --> GATESPASS{All gates pass?}
    GATESPASS -- "no" --> ROLLBACK[history/restore<br/>rollback proof]
    ROLLBACK --> CLAIM
    GATESPASS -- "yes" --> POST[Snapshot after edits]
    POST --> BRANCH[git/branch + commit-owned]
    BRANCH --> PUSH[git/push]
    PUSH --> PR[git/pr — open GitHub PR]
    PR --> EVIDENCE[Append final evidence<br/>release files + task]
    EVIDENCE --> END([PR live — Codex/User reviews])

    style BLOCK0 fill:#ff5050,color:#fff
    style READY fill:#ff8800
    style MINIMAX fill:#ff5050,color:#fff
    style DEEPSEEK fill:#ff5050,color:#fff
```

> **Current blocker is at MINIMAX/DEEPSEEK** (red nodes) — both providers return HTTP 401 from configured keys. All other steps are wired and ready.

---

## 3. Source OS 60-App Runtime Ladder

```mermaid
flowchart LR
    subgraph SRC["Source Stage (60 apps)"]
        SRC60[60 source-backed rows<br/>YAML registry]
    end

    subgraph DETECT["Detection Stage"]
        SOURCE_REF[18 source_reference_only<br/>archives, firmware, catalogs]
        DETECTED[Source detected<br/>install_state=installed]
    end

    subgraph VERIFIER["Verifier Registration"]
        READONLY[8 read_only_runner<br/>API/import probes]
        EXEC_PATH[3 executable_path<br/>launcher metadata]
        PY_IMPORT[5 python_import_repair<br/>Python module probes]
        CLI_CFG[2 cli_install_config<br/>schema/profile reads]
        NPM[1 npm_package_preflight<br/>node metadata]
        DESKTOP_GAP[3 desktop_app_runner_gap<br/>FreeCAD, SolveSpace, MatterControl]
        GPU_GAP[3 gpu_worker_runner_gap<br/>Hunyuan3D, TRELLIS, TripoSR]
    end

    subgraph EXEC["Agent-Executable Stage"]
        CLI_READY[7 agent_cli_ready<br/>Hermes Agent, Blender, OpenSCAD,<br/>CuraEngine, FLSUN, OrcaSlicer, PrusaSlicer]
    end

    subgraph BLOCKED["Blocked / Repair"]
        REPAIR[15 runtime_repair_required<br/>health verification needed]
        BLOCKED_X[2 blocked<br/>Slic3r, SuperSlicer]
        METADATA[5 metadata_ready_needs_runner<br/>dry-run smoke needed]
    end

    SRC60 --> SOURCE_REF
    SRC60 --> DETECTED
    DETECTED --> READONLY
    DETECTED --> EXEC_PATH
    DETECTED --> PY_IMPORT
    DETECTED --> CLI_CFG
    DETECTED --> NPM
    DETECTED --> DESKTOP_GAP
    DETECTED --> GPU_GAP
    DETECTED --> METADATA
    DETECTED --> REPAIR
    READONLY --> CLI_READY
    EXEC_PATH --> CLI_READY
    PY_IMPORT --> CLI_READY
    CLI_CFG --> CLI_READY
    NPM --> CLI_READY
    METADATA --> CLI_READY
    DESKTOP_GAP --> CLI_READY
    GPU_GAP --> CLI_READY
    REPAIR --> CLI_READY

    style CLI_READY fill:#3fb950,color:#fff
    style BLOCKED_X fill:#ff5050,color:#fff
    style SOURCE_REF fill:#888,color:#fff
```

---

## 4. UI No-Fake Verification Flow

```mermaid
flowchart TD
    A[ui/src/App.tsx<br/>entry] --> B[scan_active_ui_no_fake.py<br/>walks imports]
    B --> C[Collect 81 production files]
    C --> D{File contains:<br/>mock/fake/simulated/<br/>placeholder/dummy?}
    D -- yes --> FAIL[FAIL — flag file]
    D -- no --> E{import.meta.env.DEV<br/>branch?}
    E -- yes --> FAIL
    E -- no --> F{adapter call goes to<br/>/api/* via adapters.live.ts?}
    F -- no --> WARN[WARN — non-API data]
    F -- yes --> G[file is production-clean]
    G --> SUMMARY[Summary: 81 files clean<br/>0 fake markers]
    FAIL --> CIBLOCK[CI Layer F honesty gate<br/>blocks merge]
    SUMMARY --> PASS[PR cleared on UI no-fake check]

    style PASS fill:#3fb950,color:#fff
    style FAIL fill:#ff5050,color:#fff
```

---

## 5. Provider / Sandbox / CLI Trust Boundary

```mermaid
flowchart TD
    subgraph TRUSTED["Hermes3D backend (trusted process)"]
        ENV[private env loader<br/>G:/private/.env]
        LOCKS[hermes3d-locks MCP<br/>same-owner lock enforcement]
        EVIDENCE[Hash-chained evidence ledger]
        PROOF[Proof artifact directory]
    end

    subgraph PROV["Provider Lanes (network egress)"]
        MINIMAX_P[MiniMax<br/>api.minimax.io<br/>HTTP 401 BLOCKED]
        DEEPSEEK_P[DeepSeek<br/>api.deepseek.com<br/>HTTP 401 BLOCKED]
        OPENROUTER[OpenRouter<br/>fallback]
        AZURE[Azure Speech<br/>STT/TTS]
    end

    subgraph SANDBOX["Sandbox (process isolation)"]
        DOCKER[Docker container<br/>ghcr.io/openhands/openhands:latest<br/>393 MB, network=none]
        OPENCODE[OpenCode 1.4.3-hermes3d<br/>write_allowed=false]
        OPENHANDS[OpenHands 1.16.0<br/>write_allowed=false]
        DENIED[Denied paths:<br/>.git, proof, var, G:/private, node_modules]
    end

    subgraph EXTERNAL["External (denied)"]
        ARGS[CLI args with secrets]
        LOGS_LEAK[Logs with bare keys]
        FRONTEND[Frontend bundles]
    end

    TRUSTED -- "Bearer at request time" --> PROV
    TRUSTED -- "task-scoped env" --> SANDBOX
    SANDBOX -. "HTTP/2 mTLS, cwd-bounded" .-> TRUSTED
    PROV -. "HTTP 200/401, redacted blocker" .-> EVIDENCE
    SANDBOX -. "stdout/stderr redacted" .-> PROOF

    TRUSTED -. "NEVER" .-> ARGS
    TRUSTED -. "NEVER" .-> LOGS_LEAK
    TRUSTED -. "NEVER" .-> FRONTEND

    style MINIMAX_P fill:#ff5050,color:#fff
    style DEEPSEEK_P fill:#ff5050,color:#fff
    style ARGS fill:#222,color:#f88
    style LOGS_LEAK fill:#222,color:#f88
    style FRONTEND fill:#222,color:#f88
```

---

## 6. Codex Takeover Queue

```mermaid
gantt
    title Codex Takeover Queue (after Tier 0 user action)
    dateFormat YYYY-MM-DD
    axisFormat %m-%d

    section Tier 0 BLOCKER
    User: replace API keys+restart      :crit, t0, 2026-05-08, 1d

    section Tier 1 Agent loop e2e
    Pick smallest reversible target     :t1a, after t0, 1d
    First MiniMax+DeepSeek loop         :crit, t1b, after t1a, 1d
    Patch apply + gates + PR            :t1c, after t1b, 1d
    Rollback drill                      :t1d, after t1c, 1d
    First-loop proof JSON               :t1e, after t1d, 1d

    section Tier 2 Runner gaps
    MeshLab CLI                         :t2a, after t1e, 1d
    Slic3r/Strec3D/SuperSlicer          :t2b, after t2a, 1d
    FreeCAD/SolveSpace/MatterControl    :t2c, after t2b, 2d
    GPU dependency verifiers            :t2d, after t2c, 2d
    npm metadata + python imports       :t2e, after t2d, 2d
    Service+web health 9 modules        :t2f, after t2e, 3d

    section Tier 3 Update Center
    Orchestrator scaffold               :t3a, after t2f, 2d
    SmokeGate adapters                  :t3b, after t3a, 3d
    Self-update lane                    :t3c, after t3b, 2d
    Release watch                       :t3d, after t3c, 2d
    Approval policy                     :t3e, after t3d, 1d
    UI density polish                   :t3f, after t3e, 2d

    section Tier 4 Action catalog
    Audit script                        :t4a, after t1e, 1d
    Source/Settings/Plugins rows        :t4b, after t4a, 2d
    Autopilot/Voice/Design/Gen3D rows   :t4c, after t4b, 2d
    Per-row safety/approval/proof fields:t4d, after t4c, 1d
    CI parity gate                      :t4e, after t4d, 1d
```

---

## Appendix: Diagram Notes

- All diagrams reference live state at 2026-05-08 17:30Z from `http://127.0.0.1:8765`.
- Red nodes indicate current blockers (provider HTTP 401, blocked slicers, denied secret paths).
- Green nodes indicate operational/ready surfaces (CLI-ready apps, PR loop endpoints).
- Gray nodes indicate reference-only (no runner needed) or excluded paths.
- The Codex queue Gantt is illustrative — actual durations depend on Tier 0 unblock timing and provider stability.
