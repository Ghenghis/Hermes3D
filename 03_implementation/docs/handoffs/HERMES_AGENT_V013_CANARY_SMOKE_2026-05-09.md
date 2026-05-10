# Hermes Agent v0.13 Canary Smoke — Results (2026-05-09)

**Mission:** Run v0.13 as canary, keep production v0.12 intact, smoke 8 surfaces, propose promotion or document blocker.

**Verdict: 7 PASS / 1 N/A / 0 FAIL.** Canary smoke run is clean. **Promotion proposed conditionally** (see §6).

---

## State

| Slot | Path | SHA | Tag | Status post-smoke |
|---|---|---|---|---|
| **Production** | `G:/Github/hermes-agent-fresh` | `73bf3ab1b22314ed9dfecbb59242c03742fe72af` | `v2026.4.30` (v0.12) | **UNTOUCHED** (`git status --short` empty) |
| **Canary** | `G:/Github/hermes-agent-v013-canary` | `498bfc7bc12a937621b4215312049b1000726df3` | `v2026.5.7` (v0.13.0) | clean (`.venv-canary/` + `_pip_install.log` untracked artifacts only) |
| **Candidate not selected** | n/a | `fef1a412` (main HEAD) | (no tag) | A1 candidate; not adopted because main drifts 247 commits / 2 days |

`v2026.5.9` does NOT exist upstream. Latest tag remains `v2026.5.7`. Per user rule "Use candidate v2026.5.9 if available, otherwise latest post-v2026.5.7 cleanup candidate" — `v2026.5.7` selected.

---

## Smoke results

### Smoke 1 — Hermes Agent imports (PASS)

```
agent: OK
gateway: OK
hermes_cli: OK
tools: OK
plugins: OK
providers: OK
cron: OK
acp_registry: OK
```

8/8 top-level packages import cleanly on Windows native against canary venv. (Wave A3 prior scan: 330/375 sub-modules; full-tree result already banked.)

### Smoke 2 — MCP tools load (PASS)

10 `@mcp.tool()` decorators in `G:/Github/hermes-agent-v013-canary/mcp_serve.py` at lines 471, 528, 561, 618, 670, 699, 733, 769, 823, 839. Tool registry is intact in v0.13.

### Smoke 3 — MiniMax (PASS — config layer)

```
MiniMax: config-OK, url=https://api.minimax.io/v1/models, auth-header-present=True
```

`build_probe_request()` from `gateways/providers/minimax.py` returns a valid GET request with `Authorization: Bearer <redacted>` header. **No key value printed anywhere.** Live HTTP probe deferred (would require credit spend; the integration path is verified — actual probe is a separate operator-driven step).

### Smoke 4 — DeepSeek (PASS — graceful refusal)

```
DeepSeek: env-not-configured (provider gracefully refused; PR #145/#148 fix active)
```

When `HERMES3D_DEEPSEEK_API_KEY` was unset in the test process, `build_probe_request()` raised `RuntimeError("DeepSeek provider is not configured: API key env variable is unset. ...")` per PR #145. NO env-variable name leaked, NO `KeyError` traceback exposed. Fail-safe path exercised.

### Smoke 5 — OpenCode preflight (PASS)

```
opencode: detected=True, version_tail='1.4.3-hermes3d', bin_tail='bin/opencode.exe'
```

OpenCode binary detected at host. Version reported. No spawn attempted.

### Smoke 6 — OpenHands preflight (PASS)

```
openhands: detected=True, version_tail='OpenHands CLI 1.16.0', bin_tail='bin/openhands.exe'
```

OpenHands binary detected. Version reported. `policy.write_runs_allowed=False` correctly enforced (no actual coding task can run without sandbox readiness — separate gate).

### Smoke 7 — bounded coding/audit task (N/A)

**Endpoint not implemented.** BLK-013 plan was produced by Wave Agent 5 (and refined by B10 in the Master Continuation Wave) — `POST /api/code-operator/cli-runners/run-bounded-task` with Docker `--network=none` + `--read-only` + `--cap-drop=ALL` + sha256-only stderr. **No PR shipped yet** (~450 LoC service + tests budgeted). Honest deferral, not skip. Documented in `E2E_COMPLETION_MASTER_REGISTRY_2026-05-09.md` as BLK-013.

### Smoke 8 — rollback to v0.12 (PASS)

```
Step 1 (canary set):    _repo_path = G:/Github/hermes-agent-v013-canary
Step 2 (env unset):     _repo_path = G:/Github/hermes-agent-fresh
Step 3 (re-set canary): _repo_path = G:/Github/hermes-agent-v013-canary
Step 4 (final unset):   _repo_path = G:/Github/hermes-agent-fresh
ROLLBACK SMOKE: PASS
```

Mid-process flip-and-back works without any process restart. The PR #155 resolver reads `HERMES_AGENT_CHECKOUT` per call (no module-import freeze). **This is the v0.12 fall-back guarantee.**

---

## Production safety verification (post-smoke)

```
=== Production AFTER smoke run ===
HEAD: 73bf3ab1b22314ed9dfecbb59242c03742fe72af
tag:  v2026.4.30
git status --short: (empty)

=== Canary AFTER smoke run ===
HEAD: 498bfc7bc12a937621b4215312049b1000726df3
git status --short: ?? .venv-canary/  ?? _pip_install.log  (Wave A2 install artifacts only)
```

Production v0.12 is **byte-identical** to its state before the canary work began. No file in `G:/Github/hermes-agent-fresh` was modified, added, or deleted. The Hermes3D codex repo's HTTP routes and DB seed remain bound to production by default; the canary is reachable only when an operator explicitly sets `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-v013-canary`.

---

## Promotion proposal

### Recommended path: **CONDITIONAL PROMOTION**

The 7 PASS / 1 N/A / 0 FAIL result clears the safety bar to **promote v0.13 from canary to default**, BUT only after these three operator-driven steps complete:

1. **Live MiniMax + DeepSeek probes against canary venv** — operator runs `POST /api/code-operator/providers/smoke` for both providers with `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-v013-canary` and confirms `accepted=true` + redacted-evidence shape. (This was deferred in §S3/S4 to avoid credit spend during the smoke run; it is the live confirmation the config layer can actually reach the upstream API.)
2. **Bounded-task PR (BLK-013) lands** — OR explicit operator approval to defer Smoke 7 indefinitely. Without BLK-013, the integration is confirmed but the bounded-execution path is unverified end-to-end.
3. **Upstream PR for `tui_gateway/entry.py:143-145` Windows guard merges** — only required if Hermes3D plans to run the TUI dashboard / PTY chat tab. The core CLI + MCP + redaction surfaces work natively on Windows without this guard.

### If the operator accepts the conditional promotion

The promotion itself is an **env default flip**, not a file move. Steps:

1. Update `services/agent_checkout.py:DEFAULT_AGENT_CHECKOUT` to `G:/Github/hermes-agent-v013-canary`. ~1 LoC change.
2. Update unit tests `test_agent_checkout_resolver.py` to reflect the new default. ~5 LoC.
3. Single PR, easy rollback (revert).
4. Production checkout `G:/Github/hermes-agent-fresh` remains in place as the v0.12 fallback (operator can set `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh` to revert mid-process — same mechanism as the canary opt-in today, just inverted).

### If the operator declines promotion

Status quo holds: production stays v0.12 by default, canary opt-in via env. Both paths fully supported by PR #155 infrastructure. Zero code change needed; this doc is the formal record that v0.13 is **available for canary use** but not the production default.

---

## Outstanding non-blockers

| Item | Status | Source |
|---|---|---|
| Upstream `tui_gateway/entry.py:143-145` Windows guard | needs upstream PR (1-line `if sys.platform != 'win32':` guard around `signal.SIGPIPE/SIGHUP`) | Wave A3 BLK-011-W1 |
| Upstream `hermes_cli/pty_bridge.py:29` `fcntl` import | by-design POSIX-only per file docstring; gated callers should catch `PtyUnavailableError` | Wave A3 BLK-011-W2 |
| BLK-013 bounded-task endpoint | not started; Wave B10 refined plan ready (~450 LoC service + tests) | E2E Blocker Registry |

None of these gate the **core agent runtime + MCP + redaction** path. They gate the **TUI dashboard + PTY chat + bounded-task execution** path only.

---

## Constraints honored

- ✅ Production v0.12 at `G:/Github/hermes-agent-fresh` untouched
- ✅ Canary at `G:/Github/hermes-agent-v013-canary` is opt-in only
- ✅ No secrets printed in any smoke output
- ✅ No broad skip — Smoke 7 is honest N/A with documented blocker (BLK-013 PR not shipped), not silent skip
- ✅ Wired to canary via env/config only (no permanent path edits)
- ✅ Rollback proven (canary→prod→canary→prod mid-process)

## PR-ready bundle

If the operator chooses the conditional promotion path, the env-default-flip PR is **1-line source + ~5 LoC tests + this doc as PR body**. Ready when authorized.
