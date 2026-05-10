# Security, MCP, and Agent Access Audit

Generated: 2026-05-07T01:03 UTC
Sources: Audit 5 (PR #76), Lane #56 (security-mcp), Codex PR #73
Task: `H3D-CLAUDE-POLISH-AGENT-MCP-PROOF-2026-05-06`
Verdict: **PASS**

---

## Security Boundaries Verified

### Path Traversal

All file-serving routes (`/api/artifacts/proof/{filename}`, `/api/artifacts/list`) were audited. Each:
- Resolves the filename against a fixed `PROOF_DIR` constant using `Path(PROOF_DIR) / filename`
- Calls `path.resolve()` and verifies the result is still within `PROOF_DIR` before serving
- Returns HTTP 400 if traversal is detected (`../../etc/passwd` style inputs rejected)

**Verdict: PASS — no path traversal vulnerability in any artifact route.**

### Secret Redaction

All backend routes were checked for secret value leakage:
- No route returns raw `.env` values or API key contents
- Voice TTS backend proxies the Azure/ElevenLabs call — the frontend never sees the API key
- `GET /api/settings/provider-health` returns health status only (not key values)
- `GET /api/gen3d/providers` returns availability status only (not credentials)

Secret storage convention: `G:/private/.env` — outside all repo workspaces. No `.env` file is committed in any Claude lane branch.

**Verdict: PASS — no secret leakage in any visible route.**

### Shell Execution / Command Runner

No Claude lane introduces arbitrary shell execution. The only command-runner patterns found:
- `subprocess.run(["slicer-binary", "--version"])` in verifier scripts — allowlisted binary paths, no shell=True
- `subprocess.run(["pio", "--version"])` in firmware verifier — allowlisted
- All subprocess calls use `shell=False` (explicit arg lists)
- No `os.system()` or `subprocess.run("...", shell=True)` in lane-owned files

**Verdict: PASS — no arbitrary shell execution.**

### Prompt/Tool Poisoning

Lane #56 (`claude/security-mcp`) audited all Hermes Agent action contracts for:
- Tool call inputs that could inject shell commands via agent prompt
- Action contracts that echo untrusted user input back to a subprocess

No such patterns found. All agent-callable actions are allowlisted by name in the action catalog.

**Verdict: PASS — no prompt/tool poisoning vector found.**

### stdout Contamination

All proof event writers use structured JSON output. No lane writes raw user-controlled strings to stdout that could be mistaken for structured data by an upstream pipe.

**Verdict: PASS.**

---

## MCP Lock Workflow Compliance

Every Claude lane followed the required sequence:
1. `hermes_a2a_create_task` → submit
2. `hermes_claim_task` → claimed
3. `hermes_lock_files` → locked
4. `hermes_heartbeat` → maintained during work
5. (edit files)
6. `hermes_append_evidence` → hash-chained
7. `hermes_release_files` → released (by orchestrator at handoff)
8. `hermes_release_task` → released

The orchestrator itself claimed task `H3D-CLAUDE-ORCHESTRATOR-*` before baseline commits and before dispatching sub-agents.

**No ghost editing (editing without an active Hermes lock) was performed by any Claude agent.**

---

## Codex PR #73 — Hermes Agent Code Operator

PR #73 (`codex/hermes-agent-mcp-code-operator`) is a **Codex-owned DRAFT**. It adds:
- MCP-locked code execution for Hermes Agents
- Pre/post snapshot requirement before any source patch
- Gate requirement (`hermes_run_gate`) before patch application
- Evidence chaining for all code-operator actions

### What Hermes Agents CAN do after PR #73 merges

- Propose code patches (with active same-owner MCP lock)
- Run allowlisted gate commands (`tsc --noEmit`, `pytest`, `py_compile`)
- Append evidence to the Hermes ledger
- Read files in their locked scope

### What Hermes Agents CANNOT do after PR #73 merges

- Apply source changes without active same-owner MCP lock (403 returned)
- Apply source changes without pre/post snapshots (gate rejects)
- Execute arbitrary shell commands (not in allowlist → blocked)
- Access files outside their locked scope (path resolution check)
- Return secret values from any backend route (redaction layer)

**PR #73 status: DRAFT, CLEAN. Codex merges when code-operator feature is complete.**

---

## Hermes Evidence Chain Integrity

All Claude agent evidence entries are hash-chained. Each entry includes:
- `prev_entry_id` and `prev_hash` referencing the previous entry
- `entry_hash` computed over current content + prev_hash

This creates a tamper-evident audit trail. The orchestrator's evidence chain for the 6-agent audit pass:
- Audit 1 evidence: task `H3D-CLAUDE-POLISH-MERGE-2026-05-06`, PR #75
- Audit 2 evidence: task `H3D-CLAUDE-POLISH-NOFAKE-UI-2026-05-06`, PR #79
- Audit 3 evidence: task `H3D-CLAUDE-POLISH-SOURCE-RUNTIME-2026-05-06`, PR #74
- Audit 4 evidence: task `H3D-CLAUDE-POLISH-PRINTER-SAFETY-2026-05-06`, PR #77
- Audit 5 evidence: task `H3D-CLAUDE-POLISH-AGENT-MCP-PROOF-2026-05-06`, PR #76
- Audit 6 evidence: task `H3D-CLAUDE-POLISH-RELEASE-DOCS-2026-05-06`, PR #78
- TS7026 fix evidence: task `a2a_1778114702912_1ac758ea`, PR #80
- Final handoff evidence: task `a2a_1778115796454_685e7b14`, this PR

**Hermes evidence chain: PASS — all entries chained and consistent.**
