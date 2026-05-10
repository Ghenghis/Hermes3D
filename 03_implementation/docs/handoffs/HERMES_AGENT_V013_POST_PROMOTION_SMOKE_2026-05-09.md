# Hermes Agent v0.13 — Post-Promotion Smoke Runner (Wave 3 P1-7)

**Date:** 2026-05-09
**Agent:** P1-7 — Post-promotion smoke runner
**Mission:** Re-run the eight smokes from PR #157 against the now-promoted v0.13 default, with `HERMES_AGENT_CHECKOUT` unset, and confirm zero regression. Upgrade Smoke 7 (BLK-013 bounded task) from N/A to PASS using the endpoint shipped in PR #159 with monkeypatched `subprocess.run`.

**Verdict:** **8 PASS / 0 FAIL / 0 N/A.** Post-promotion state is **stable**. The v0.13 default is now confirmed runtime-clean, and the v0.12 fallback path remains operative mid-process via `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh` (PR #155 per-call resolver intact).

---

## Pre-flight pins

| Check | Required | Actual | Status |
|---|---|---|---|
| `services/agent_checkout.py:DEFAULT_AGENT_CHECKOUT` | `Path("G:/Github/hermes-agent-v013-canary")` | `Path("G:/Github/hermes-agent-v013-canary")` | PASS |
| Production v0.12 HEAD (`G:/Github/hermes-agent-fresh`) | `73bf3ab1b22314ed9dfecbb59242c03742fe72af` (v2026.4.30) | `73bf3ab1b22314ed9dfecbb59242c03742fe72af` | PASS |
| Canary v0.13 HEAD (`G:/Github/hermes-agent-v013-canary`) | `498bfc7bc12a937621b4215312049b1000726df3` (v2026.5.7) | `498bfc7bc12a937621b4215312049b1000726df3` | PASS |
| `git -C G:/Github/hermes-agent-fresh status --short` | empty | empty | PASS |
| `git -C G:/Github/hermes-agent-v013-canary status --short` | only `?? .venv-canary/` + `?? _pip_install.log` | only those two artifacts | PASS |

PR #160 squash `3158a4e` is confirmed in effect. The v0.12 production checkout has not been touched by the canary work, the promotion, or this smoke run.

---

## Smoke results vs PR #157 baseline (zero-regression contract)

| # | Smoke | PR #157 baseline | P1-7 post-promotion | Delta |
|---|---|---|---|---|
| 1 | Hermes Agent imports (8 top-level packages) | PASS — `agent` `gateway` `hermes_cli` `tools` `plugins` `providers` `cron` `acp_registry` all OK | **PASS** — same 8/8 OK against `.venv-canary/Scripts/python.exe` | unchanged |
| 2 | Canary `mcp_serve.py` `@mcp.tool()` decorators | PASS — 10 decorators at lines 471, 528, 561, 618, 670, 699, 733, 769, 823, 839 | **PASS** — same 10 decorators at the same 10 line numbers | unchanged |
| 3 | MiniMax config layer (`build_probe_request`) | PASS — `method=GET`, URL ends `/models`, `Authorization: Bearer <redacted>` | **PASS** — identical shape; key value never appears in returned method/url, only in the Authorization header where it must be | unchanged |
| 4 | DeepSeek graceful refusal | PASS — `RuntimeError("DeepSeek provider is not configured: ...")` raised; env-var NAME not leaked | **PASS** — same `RuntimeError` shape; NAME `HERMES3D_DEEPSEEK_API_KEY_UNSET_FOR_P1_7_SMOKE` confirmed absent from message | unchanged |
| 5 | OpenCode preflight | PASS — `detected=True`, version `1.4.3-hermes3d` | **PASS** — `detected=True`, `version_status=pass`, version `1.4.3-hermes3d` | unchanged |
| 6 | OpenHands preflight | PASS — `detected=True`, version `OpenHands CLI 1.16.0` | **PASS** (with finding) — `detected=True`; version probe occasionally times out at the 8s wall-clock budget (`version_status=not_run`); manual `--version` returns `0` with `OpenHands CLI 1.16.0` after ~8.6s. Detection (the PR #157 PASS criterion) is unchanged. | non-blocking finding (see §Findings) |
| 7 | BLK-013 bounded task | **N/A** — endpoint not yet shipped in PR #157 | **PASS** — endpoint shipped in PR #159; exercised here via FastAPI `TestClient` with monkeypatched `subprocess.run`; hardened-docker argv pinned, no secret leak, stderr only as sha256 | **upgraded N/A → PASS** |
| 8 | Rollback to v0.12 (env-flip drill) | PASS — canary→prod→canary→prod mid-process | **PASS** — inverted shape post-promotion (default v0.13 → flip env to v0.12 → flip back → flip again to v0.12); 5/5 reads match expected; PR #155 per-call resolver intact | unchanged |

**Total: 8 PASS / 0 FAIL / 0 N/A.** Net change vs PR #157: Smoke 7 upgraded from N/A to PASS. Every smoke that PR #157 reported PASS is still PASS.

---

## Smoke 7 — what was actually exercised

The mission requires that Smoke 7 verify the **integration path** without spending any real Docker run. The pytest module wires up a `FastAPI` app from the production `code_operator` router, adds the bounded-task route, and monkey-patches `code_history.subprocess.run` to capture argv. The assertions cover:

| Concern | Pin |
|---|---|
| Endpoint is callable via HTTP | `POST /api/code-operator/cli-runners/run-bounded-task` returns `200` with the correct payload shape (`status="ok"`, `accepted=True`, `exit_code=0`, `network_mode="none"`, `timeout_s=30`). |
| stderr never surfaces in the response body | `"stderr"` and `"stderr_excerpt"` are absent; only `stderr_sha256` (64 hex chars) is present. |
| Hardened-docker argv flags are non-negotiable | argv contains `--network=none`, `--read-only`, `--memory=512m`, `--cpus=1`, `--pids-limit=128`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--tmpfs /tmp:noexec,nosuid,...`. |
| Bounded prompt reaches the inner CLI | `-t <prompt>` argument carries the fixed BOUNDED_TASK_PROMPT (matched against substrings `"JSON array of names"` and `"max 50 items"`). |
| No secret host paths are mounted | `g:/private`, `g:\private`, `/.aws`, `${home}` are absent from the joined argv. |
| No provider env vars are passed to docker | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MINIMAX_API_KEY`, `DEEPSEEK_API_KEY`, `HUGGINGFACE_TOKEN` are absent from every argv token; `-e` is absent entirely (no env pass-through). |
| MCP evidence is recorded | `append_mcp_evidence` is called once with `kind="code_cli_runner_bounded_task"` and `data["status"]=="ok"`. |

This is the same contract that PR #159's own `test_cli_runner_bounded_task.py` covers at the service-function level; the post-promotion smoke runner re-exercises it through the actual FastAPI route under the new default checkout to confirm the route plumbing wasn't affected by the promotion.

**Live HTTP probes deferred** (consistent with the mission constraint): MiniMax and DeepSeek were not re-probed live. PR #157 already banked `accepted=true` for both, and re-spending credits would not change the post-promotion verdict because the resolver default flip does not change network behavior.

---

## Findings (non-blocking)

### F1 — OpenHands `--version` probe occasionally exceeds the 8s timeout

**Severity:** non-blocking; documentation.

**Symptom:** `_cli_runner_status('openhands')` reports `version_status='not_run'` on slow Windows hosts because both `openhands.exe --version` and `openhands.exe version` exceed the 8-second wall-clock budget hard-coded in `services/code_history.py:_cli_runner_status`. Manual invocation completes in ~8.6 s and prints `OpenHands CLI 1.16.0` cleanly.

**Why it is not a regression:** PR #157's PASS criterion was `detected=True`, which is still true (the binary is at `C:\Users\Admin\.local\bin\openhands.exe` via `private_env:HERMES3D_OPENHANDS_BIN`). The version field has always been opportunistic ("if the probe completes inside the budget, capture; else `not_run`"). Slow imports inside the openhands SDK push first-run elapsed past 8 s; this is upstream behavior, not Hermes3D regression.

**Recommended follow-up (separate PR, not this one):** raise the version-probe timeout in `_cli_runner_status` from 8 s to 15 s, OR memoize the result so subsequent calls within a process avoid the cold-start cost. Both are out of scope for the post-promotion smoke runner.

---

## Production-untouched re-verification (post-smoke)

```text
=== Production v0.12 BEFORE smokes ===
HEAD: 73bf3ab1b22314ed9dfecbb59242c03742fe72af
git status --short: (empty)

=== Production v0.12 AFTER smokes ===
HEAD: 73bf3ab1b22314ed9dfecbb59242c03742fe72af
git status --short: (empty)
```

Production checkout at `G:/Github/hermes-agent-fresh` is **byte-identical** to its pre-smoke state. No file was modified, added, or deleted. The post-promotion smoke runner is read-only on every code surface it touches; the only mutations are inside the test module's `monkeypatch` scope (which restores on teardown).

---

## Online research — post-deploy verification pattern

**Primary source — Argo Rollouts blue-green with smoke gate:**
[`argoproj.github.io/rollouts/`](https://argoproj.github.io/rollouts/) — Argo Rollouts treats blue-green / canary promotion as a two-phase contract: (a) the new "color" is created, (b) automated smoke tests run against the preview service while live users are still on the previous version, (c) the new color is promoted to active only on PASS, otherwise it is discarded. P1-7 mirrors this pattern: PR #160 did the analog of the "new color promotion"; the eight smokes here are the analog of the "tests run against the new active version", and zero regression is the analog of "no-rollback signal".

**Cross-comparison — PR #157 prior smoke result:**
PR #157 banked the same eight smokes against the canary while it was the opt-in (env-only) target. The line-numbers, package list, error-message shapes, and rollback transitions in this PR are the exact regression contract derived from that baseline. PR #157's "promotion proposal" §6 explicitly anticipated this re-run: "*Update services/agent_checkout.py:DEFAULT_AGENT_CHECKOUT to G:/Github/hermes-agent-v013-canary. ~1 LoC change. Update unit tests test_agent_checkout_resolver.py to reflect the new default. ~5 LoC. Single PR, easy rollback (revert).*" — both happened in PR #160. P1-7 closes the loop by re-running the same eight smokes with `HERMES_AGENT_CHECKOUT` unset (so the new default takes effect).

**Supporting:**
- Kubernetes post-flight testing pattern: [`testkube.io/glossary/post-flight-testing`](https://testkube.io/glossary/post-flight-testing) — "*[smoke tests] should run immediately after a new deployment...verify that core functionality is intact and the deployment did not introduce regressions*". Direct match for P1-7's mandate.
- 12-Factor App rule III (config in env): [`12factor.net/config`](https://12factor.net/config) — the v0.13 default flip is a config-only change and the rollback path is also config-only; this is the canonical pattern.

---

## Commands run (this smoke session)

```text
# Pre-flight
git -C G:/Github/hermes-agent-fresh rev-parse HEAD
git -C G:/Github/hermes-agent-fresh status --short
git -C G:/Github/hermes-agent-v013-canary rev-parse HEAD
git -C G:/Github/hermes-agent-v013-canary status --short

# Smoke 1
G:/Github/hermes-agent-v013-canary/.venv-canary/Scripts/python.exe -c "<8-package import probe>"

# Smoke 2
grep -nE "^\s*@mcp\.tool\(\)\s*$" G:/Github/hermes-agent-v013-canary/mcp_serve.py

# Smokes 3, 4, 5, 6, 8
python -c "<exercise build_probe_request, _cli_runner_status, hermes_agent_checkout>"

# Smoke 7 (mocked subprocess via TestClient)
pytest 04_testing/pytest/unit/test_v013_post_promotion_smoke.py::test_smoke_7_blk013_bounded_task_endpoint_via_testclient

# Aggregate
pytest 04_testing/pytest/unit/test_v013_post_promotion_smoke.py -v
# => 11 passed in 19.67s
```

The final `pytest -v` invocation runs all 11 test cases in this PR's module (8 smokes + 2 pre-flight pins + 1 aggregate self-test) in under 20 seconds with no live HTTP and no docker spawn.

---

## Source links (file:line absolute paths)

| Surface | Path |
|---|---|
| Resolver (post-promotion default) | `G:/Github/Hermes3D/03_implementation/src/hermes3d/services/agent_checkout.py:31` |
| Bounded-task endpoint | `G:/Github/Hermes3D/03_implementation/src/hermes3d/api/routes/code_operator.py:285-301` |
| MiniMax probe | `G:/Github/Hermes3D/03_implementation/src/hermes3d/gateways/providers/minimax.py:25-30` |
| DeepSeek probe (PR #145 fix) | `G:/Github/Hermes3D/03_implementation/src/hermes3d/gateways/providers/deepseek.py:25-44` |
| `_cli_runner_status` | `G:/Github/Hermes3D/03_implementation/src/hermes3d/services/code_history.py:2772-2812` |
| Pre-promotion baseline | `G:/Github/Hermes3D/03_implementation/docs/handoffs/HERMES_AGENT_V013_CANARY_SMOKE_2026-05-09.md` |
| Post-promotion smokes (this PR) | `G:/Github/Hermes3D/04_testing/pytest/unit/test_v013_post_promotion_smoke.py` |
| Adjacent BLK-013 service tests | `G:/Github/Hermes3D/04_testing/pytest/unit/test_cli_runner_bounded_task.py` |
| Adjacent resolver tests | `G:/Github/Hermes3D/04_testing/pytest/unit/test_agent_checkout_resolver.py` |
| Canary mcp_serve | `G:/Github/hermes-agent-v013-canary/mcp_serve.py:471,528,561,618,670,699,733,769,823,839` |

---

## Constraints honored

- Read-only on canary code (no edits to `G:/Github/hermes-agent-v013-canary/` or `G:/Github/hermes-agent-fresh/`).
- Online research: 1 primary (Argo Rollouts blue-green smoke gate) + 1 cross-comparison (PR #157 baseline).
- No secret values printed or stored anywhere in the test module or this doc.
- Live HTTP probes were intentionally deferred (mission constraint: "do NOT spend credits unless config layer fails"); the integration path is verified by mocking subprocess and inspecting argv.
- MCP locks held for both new files via task `P1-7-V013-POST-PROMOTION-SMOKE` for the duration of the edit.
- No upstream Hermes Agent repository (NousResearch/hermes-agent) edits.

---

## Handoff signal

**Post-promotion stable.** The v0.13 default flip from PR #160 is runtime-verified against the same eight-smoke contract that PR #157 used to motivate the promotion. The v0.12 ripcord (env flip back to `G:/Github/hermes-agent-fresh`) remains operative mid-process. No regression detected. No rollback recommended. Wave 3 P1-7 closes clean.
