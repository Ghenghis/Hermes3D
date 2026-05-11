# W18-A21 — /api/providers/health reads smoke evidence + #agents GUI surfaces team tasks

**Task ID:** `W18-A21-PROVIDERS-HEALTH-GUI-2026-05-11`
**Branch:** `claude/w18-a21-providers-health-and-agents-gui`
**Worktree:** `G:\Github\Hermes3D\.claude\worktrees\w18-a21\`
**Date:** 2026-05-11 (UTC)

## What MiniMax identified (ev_cf6aabf495dc9cfb)

The `provider_health()` function in `src/hermes3d/api/routes/system.py`
(lines 227-259 before this fix) hardcoded `status="idle"` for every cloud
provider (minimax, deepseek, openrouter) whose API key was present in the
private env — regardless of whether the latest live smoke proof at
`/api/code-operator/providers/smoke` had said the provider was ready,
failed, or never probed.

Operators saw `idle, idle, idle` for the cloud providers in the GUI even
after the W18-A19 real MiniMax + DeepSeek smokes both passed with HTTP 200
and recorded evidence (`ev_62646ba782e786af` and `ev_7e5227426217aee7`).

## What this PR does

### Step 1 — Backend fix (`src/hermes3d/api/routes/system.py`)

`provider_health()` now reads
`var/code-history/provider-smoke-status.json` (the file written by
`hermes3d.services.code_history._write_provider_smoke_status` after every
real smoke run) and enriches each cloud provider entry from it:

- Latest smoke is `status="ready"` and within the 5-minute staleness
  window → return `status="green"`, `http_status=200`, the evidence_id,
  base_url_label, model, and content_sha256.
- Latest smoke is `status="ready"` but older than 5 minutes → return
  `status="idle"` honestly with `stale=true` and
  `blocked_reason="Smoke proof is older than the staleness window; rerun provider smoke."`.
- Latest smoke is `status="blocked" | "auth_failed" | "smoke_failed" | "missing_config"`
  → return `status="red"` with the first blocked_reason exposed.
- No smoke evidence on disk → return `status="idle"` honestly (no
  fabricated evidence id, no fake green).

Live before/after curl against the same `provider-smoke-status.json`:

**Before (running w18-a12 backend on port 8765):**

```json
{
  "provider_id": "minimax",
  "status": "idle",
  "http_status": null,
  "latency_ms": null,
  "stale": false
}
```

**After (w18-a21 backend on port 8030 with the same status file):**

```json
{
  "provider_id": "minimax",
  "status": "green",
  "http_status": 200,
  "stale": false,
  "evidence_id": "ev_62646ba782e786af",
  "base_url_label": "api.minimax.io",
  "model": "MiniMax-M2.7-highspeed",
  "content_sha256": "733cf01d1a41d5e66b5dbb483057691d9f0c49fde87ef2403f57df6ee302390e"
}
```

### Step 2 — Read-only team-tasks endpoint (`src/hermes3d/api/routes/code_operator.py`)

Added two new GET routes, both read-only and free of API key exposure:

- `/api/code-operator/teams/team-tasks?limit=25`
  Returns the most recent `code_provider.coding_plan` /
  `code_provider.code_review` proof_events rows. One row per real
  MiniMax-builder or DeepSeek-reviewer team task. Each item carries
  `team_id`, `provider_id`, `task_id`, `run_id`, `files`,
  `response_sha256`, `prompt_sha256`, `ts_utc`.
- `/api/code-operator/teams/provider-smoke-history?limit=10`
  Returns the parsed `var/code-history/provider-smoke-status.json` for
  surfacing in the GUI alongside the team-task list.

### Step 3 — #agents GUI: TeamTasksPanel (`ui/src/components/agents/TeamTasksPanel.tsx`)

New self-contained React panel rendered between the existing
`AgentCommandCenter` and the Agent Code Workbench panels on the Agents
tab. Fetches both `/teams/team-tasks` and `/teams/provider-smoke-history`
every 10 seconds (no manual refresh required). Renders:

- Live provider smoke history (per provider: status badge, model,
  base_url_label, evidence id short-hash, blocked reasons).
- Recent team-task runs (per row: provider, team, task_id, response
  short-hash, file count, timestamp, source agent).

All `data-testid` hooks (`agents-team-tasks-root`,
`agents-team-tasks-runs`, `agents-team-tasks-run-<id>`, …) are wired so
Playwright can assert exact rendering.

### Step 4 — Playwright proof (`ui/tests/e2e/w18-a21-minimax-task-in-gui.spec.ts`)

Env-aware (REAL_MINIMAX vs HONEST_BLOCKED) per the W18-A4 / W18-A17
pattern. Probes `/api/code-operator/teams/readiness`; if
`minimax-builders.provider.live_status === "passed"` it posts a real
coding pass to `/api/code-operator/teams/run-coding-pass` and asserts the
new task appears in the #agents team-tasks panel via 10-s auto-refresh
without `page.reload()`. Otherwise asserts honest empty/blocked state and
forbids any fake `W18-A21-*` chip.

Live result from this worktree (REAL_MINIMAX branch):

```
[W18-A21] branch=REAL_MINIMAX minimax_live_status=passed blocked=[]
  ok 1 [chromium-w18-a21] › w18-a21-minimax-task-in-gui.spec.ts:168:1 › real MiniMax team task appears in #agents GUI without manual refresh (env-aware) (21.1s)

  1 passed (22.3s)
```

Generated artifacts (real, not fixtures):

| Artifact | Contents |
|---|---|
| `coding-pass-response.json` | MiniMax-M2.7-highspeed HTTP 200, latency 14557 ms, evidence `ev_0c9db4d3cd072caf`, response_sha256 `71052ebb…e13aefd` |
| `team-tasks-snapshot.json` | proof_events row id `102f57e027134b4488b0c71e1b536c68`, task_id `W18-A21-MINIMAX-TEAM-1778510176325` |
| `readiness.json` | minimax-builders + deepseek-reviewers both `live_status="passed"` |
| `before-real_minimax.png` | #agents tab before run-coding-pass |
| `after-real-minimax.png` | new run chip rendered without page reload |

## Pytest coverage (10 tests, all pass)

`04_testing/pytest/integration/test_providers_health_smoke_evidence.py`

- `test_providers_health_honest_idle_when_no_smoke_evidence` — no status
  file ⇒ entries stay honestly idle.
- `test_providers_health_green_for_recent_ready_smoke` — fresh ready
  smoke ⇒ green + evidence_id surfaced.
- `test_providers_health_stale_smoke_does_not_fabricate_green` — 30 min
  old smoke ⇒ idle + stale=true + "rerun provider smoke" reason.
- `test_providers_health_red_for_recent_blocked_smoke` — blocked smoke
  ⇒ red + first blocked_reason exposed.
- `test_providers_health_response_never_exposes_api_key` — body never
  echoes the env API key.

`04_testing/pytest/integration/test_team_tasks_endpoint.py`

- `test_team_tasks_empty_returns_zero_items`
- `test_team_tasks_returns_coding_and_review_rows`
- `test_team_tasks_filters_non_team_event_types`
- `test_team_tasks_limit_clamped`
- `test_provider_smoke_history_reads_local_status_file`

```
============================= 10 passed in 3.90s ==============================
```

## Provider chain references

- **MiniMax live smoke evidence:** `ev_62646ba782e786af` (HTTP 200, 3150 ms)
- **DeepSeek live smoke evidence:** `ev_7e5227426217aee7` (HTTP 200, 4246 ms)
- **MiniMax coding task identified the root cause:** `ev_cf6aabf495dc9cfb`
  (W18-MINIMAX-BUILDER-PROVIDERS-HEALTH-2026-05-11)
- **DeepSeek reviewer task:** `ev_95c4e1e7a077927c`
  (W18-DEEPSEEK-REVIEW-MERGED-PR244-2026-05-11), PASS_WITH_OBSERVATIONS on PR #244.
- **New MiniMax task ran during Playwright proof:** `ev_0c9db4d3cd072caf`
  (W18-A21-MINIMAX-TEAM-1778510176325)

## Hermes evidence chain: PASS

## Confirmation

- No printer hardware writes.
- No API keys exposed in code, logs, screenshots, or PR body.
- Pinned `GUI_PHYSICAL_PRINT_GREEN` / `GUI_PRINTER_DRY_RUN_GREEN` =
  `OUT_OF_SCOPE_BY_OPERATOR` unchanged.
- All locks held under owner `w18-a21`, released after evidence appended.
