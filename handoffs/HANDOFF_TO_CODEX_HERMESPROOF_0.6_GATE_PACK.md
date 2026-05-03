# HANDOFF_TO_CODEX — HermesProof v0.6: Secret + Quality + Test gate pack

> **Status:** READY for Codex pickup. **Different repo:** `G:\Github\hermes3d-mcp-lock-orchestrator` (HermesProof), not Hermes3D.
>
> **Sequence position:** Task 3 in overnight queue (after BLENDER-AUDIT).
>
> **Owner:** `codex-impl-05`.
>
> **Estimated time:** 2-4 hours.

---

## 1. Mission

Ship HermesProof v0.6 — a foundational gate pack that closes the secret-leak vector (the `.env.txt` incident on 2026-05-03), integrates two of the user's own tools (`Ghenghis/auto_linter`, `Ghenghis/agentic-testing`), and adds first-class env-var path resolution.

Five concrete additions:

1. **`secret.scan` truth gate** — gitleaks integration with custom regex pack for non-GitHub-scanned providers (Anthropic, MiniMax, DeepSeek, SiliconFlow, HuggingFace, CodeRabbit)
2. **`auto-lint-*` truth gates** — 4 gates wrapping `Ghenghis/auto_linter`: check, security, architecture, report
3. **`agentic-test-*` truth gates** — 2 gates wrapping `Ghenghis/agentic-testing`: coverage-audit, test-self-heal
4. **`HERMES3D_ENV_FILE` resolution** — first-class env-var path resolution in HermesProof's launcher, plus `HERMES3D_VPS_ENV_FILE` for the deploy bundle
5. **Hardened `.gitignore`** — catches `.env.txt`, `.env.bak`, `.env~`, `.env.swp`, `.env.deploy`, `.env2`, `*.env`, while preserving `!.env.example` and `!.env.vps.example` exceptions
6. **Pre-commit hook** — `gitleaks protect --staged --redact` so secrets can't reach a push attempt at all

---

## 2. Claim

```text
hermes_pick_task
  owner=codex-impl-hp
  prefer_task_id=CP-HERMESPROOF-0.6
```

Or fallback claim with `taskId=CP-HERMESPROOF-0.6`, `title=v0.6 — Secret + Quality + Test gate pack`, `reason=Foundational gates closing secret-leak vector + auto_linter + agentic-testing integration. Builds on v0.5.0 task queue.`

---

## 3. Branch

`feat/cp-hermesproof-0.6-gate-pack` from HermesProof's `main` (HermesProof uses `main` directly, not `develop`).

---

## 4. Lock these exact files

```text
hermes_lock_files
  owner=codex-impl-hp
  taskId=CP-HERMESPROOF-0.6
  ttlMinutes=180
  files=[
    "package.json",
    "src/server.mjs",
    "src/core/lock-manager.mjs",
    "src/core/event-manager.mjs",
    "src/core/queue-manager.mjs",
    "src/core/gate-runner.mjs",
    "scripts/truth-gates.mjs",
    "scripts/coordination-smoke-test.mjs",
    "scripts/hardening-smoke-test.mjs",
    "scripts/install-clients.mjs",
    "scripts/wizard.mjs",
    ".gitignore",
    ".gitleaks.toml",
    ".githooks/pre-commit",
    "docs/SECURITY_POLICY.md",
    "docs/TOOL_REFERENCE.md",
    "docs/MAINTENANCE.md",
    "README.md"
  ]
```

`.gitleaks.toml` and `.githooks/pre-commit` are NEW. Others are MODIFIED.

Lock list includes `event-manager.mjs` and `queue-manager.mjs` because §5.3 sets coverage thresholds against them — if Codex needs to add type hints / docstrings / minor cleanup to lift coverage, the locked-list rule must permit it. Same for `hardening-smoke-test.mjs` which is part of the test script (`package.json` test runner reads it) so new tests for secret/lint gates may belong there.

If your audit of HermesProof finds any of the listed files don't exist on `main`, file a blocked-handoff (lock-list-vs-reality contradiction) and skip to the next task. Same discipline as B1/B2.

---

## 5. Implementation contract

### 5.1 `secret.scan` gate (gitleaks integration)

**`.gitleaks.toml`** — NEW. Custom config layered on top of gitleaks default rules:

```toml
title = "HermesProof secret-scan rules"
extend.useDefault = true

[[rules]]
id = "anthropic-api-key"
description = "Anthropic API key (sk-ant-...)"
regex = '''sk-ant-[a-zA-Z0-9_-]{20,}'''
keywords = ["sk-ant-"]

[[rules]]
id = "minimax-api-key"
description = "MiniMax API key"
regex = '''(?i)minimax[_-]?(api[_-]?)?key['"\s:=]+([a-zA-Z0-9_.-]{30,})'''
keywords = ["minimax"]

[[rules]]
id = "deepseek-api-key"
description = "DeepSeek API key (requires deepseek keyword co-located within 100 chars)"
regex = '''(?i)deepseek[\s\S]{0,120}sk-[a-zA-Z0-9]{32,48}'''
keywords = ["deepseek"]

[[rules]]
id = "siliconflow-api-key"
description = "SiliconFlow API key"
regex = '''sk-[a-zA-Z0-9_-]{40,}'''
keywords = ["siliconflow"]

[[rules]]
id = "huggingface-token"
description = "Hugging Face token (hf_...)"
regex = '''hf_[a-zA-Z0-9]{30,}'''
keywords = ["hf_"]

[[rules]]
id = "coderabbit-api-key"
description = "CodeRabbit API key"
regex = '''(?i)coderabbit[_-]?(api[_-]?)?key['"\s:=]+([a-zA-Z0-9_-]{30,})'''
keywords = ["coderabbit"]

[allowlist]
description = "Permitted patterns — synthetic test keys, examples"
regexes = [
  '''sk-ant-test-[a-zA-Z0-9-]+''',  # synthetic test keys used in unit tests
  '''sk-ant-example-key''',          # README placeholders
]
paths = [
  '''.*\.example$''',                 # .env.example, .env.vps.example
  '''node_modules/.*''',              # vendored deps, not our code
  '''PROOF/.*''',                     # auto-generated proof artifacts
]
```

**`scripts/truth-gates.mjs`** — add a new gate `secret.scan`:

- Calls `gitleaks detect --config .gitleaks.toml --no-git --redact --report-format json --report-path /tmp/gitleaks-report.json --exit-code 1`
- If `gitleaks` binary not on PATH, emit a clear "gitleaks not installed; install via `brew install gitleaks` or `choco install gitleaks` or `go install github.com/gitleaks/gitleaks/v8@latest`" — and treat as `skip` only on local runs, `fail` in CI
- In CI: install gitleaks via `gitleaks/gitleaks-action@v2` (SHA-pin the action). The action runs against the PR diff
- Gate evidence: `findings_count`, `redacted_findings`, `gitleaks_version`
- Required gate (not advisory)

**`docs/SECURITY_POLICY.md`** — add a "Secret-leak prevention" section explaining:
- The 2026-05-03 `.env.txt` incident (one paragraph, no specifics)
- The two-store convention (`G:\private\` and `C:\Users\Admin\Downloads\VPS\`) — generic-language version, no actual paths committed
- The `secret.scan` gate
- The pre-commit hook
- The hardened `.gitignore`

### 5.2 `auto-lint-*` gates (Ghenghis/auto_linter integration)

**`scripts/truth-gates.mjs`** — add 4 gates:

- `auto-lint.check` — runs `auto_linter check --output sarif --output-path /tmp/auto-lint.sarif`. Required gate.
- `auto-lint.security` — runs `auto_linter security --output sarif --output-path /tmp/auto-lint-security.sarif`. Required gate.
- `auto-lint.architecture` — runs `auto_linter architecture --rules .auto-lint-rules.json`. Advisory (not gating until rules are tuned for HermesProof).
- `auto-lint.report` — runs `auto_linter report --inputs /tmp/auto-lint*.sarif --output PROOF/auto-lint-report.json`. Required gate (just publishes the aggregated report; never fails on findings; finding-count published as evidence).

**`auto_linter`** is the user's own tool at `https://github.com/Ghenghis/auto_linter`. Add it as a dev dependency. If it's published to npm/pypi, install via package.json/requirements. If not, document a `git clone + npm link` setup in `docs/MAINTENANCE.md`.

If `auto_linter` is not yet published (likely), this is a brief contradiction — write a blocked-handoff requesting clarification. The architect (Claude) will respond with a path-fix.

### 5.3 `agentic-test-*` gates (Ghenghis/agentic-testing integration)

**`scripts/truth-gates.mjs`** — add 2 gates:

- `agentic-test.coverage-audit` — runs `agentic_testing coverage --target src/ --output json`. Required gate. Fails if coverage < 80% for `src/server.mjs`, `src/core/lock-manager.mjs`, `src/core/gate-runner.mjs`, `src/core/event-manager.mjs`, `src/core/queue-manager.mjs`. Other files advisory.
- `agentic-test.self-heal` — runs `agentic_testing self-heal --dry-run --target test/`. Advisory gate. Reports tests that flake / break with a known-good fix recommendation. Never fails CI; reports findings in PROOF.

Same dependency-availability concern as 5.2.

### 5.4 `HERMES3D_ENV_FILE` resolution

**`src/server.mjs`** — at the top of `main()`, before any `process.env.X` reads, add:

```javascript
import { config as loadDotenv } from "dotenv";
import fs from "node:fs";
import path from "node:path";

// HERMES3D_ENV_FILE (general dev) takes precedence.
// HERMES3D_PROFILE=vps switches to HERMES3D_VPS_ENV_FILE.
// Falls back to ./.env if it exists (legacy in-tree pattern).
//
// Note: HermesProof's server.mjs is launched by MCP clients via stdio JSON-RPC.
// It does NOT parse process.argv for command flags. Profile selection therefore
// uses the HERMES3D_PROFILE env var (NOT a `--vps-mode` argv flag).
function resolveEnvFile() {
  const profile = (process.env.HERMES3D_PROFILE || "").toLowerCase();
  if (profile === "vps" && process.env.HERMES3D_VPS_ENV_FILE) {
    return process.env.HERMES3D_VPS_ENV_FILE;
  }
  if (process.env.HERMES3D_ENV_FILE) {
    return process.env.HERMES3D_ENV_FILE;
  }
  const localEnv = path.resolve(process.cwd(), ".env");
  return fs.existsSync(localEnv) ? localEnv : null;
}

const envFile = resolveEnvFile();
if (envFile && fs.existsSync(envFile)) {
  loadDotenv({ path: envFile });
}
```

Add `dotenv` to `package.json` dependencies (currently 2 deps — adding a 3rd is acceptable for this use case). Pin to `^16.4` or current stable.

`docs/MAINTENANCE.md` — document the resolution order:
1. `HERMES3D_PROFILE=vps` + `HERMES3D_VPS_ENV_FILE` env vars (deploy mode)
2. `HERMES3D_ENV_FILE` env var (explicit override) — recommended for users with secrets at `G:\private\.env`
3. `./.env` in current working directory (legacy fallback; ignored if `.env` doesn't exist)

DO NOT log the resolved env file path at info level. Debug-level only, redacted.

### 5.5 Hardened `.gitignore`

**`.gitignore`** — append (at the bottom of the existing file):

```gitignore
# 2026-05-03 hardening: catch secret-bearing variants the standard .env pattern misses
.env.txt
.env.bak
.env.old
.env.swp
.env~
.env.deploy
.env2
.env.production
.env.staging
.env.vps
.env.local
.env.*.local

# Catch-all for any *.env file
*.env

# But preserve documented templates
!.env.example
!.env.vps.example
!.env.deploy.example
```

`.env` itself is already there from earlier hardening. Don't duplicate.

### 5.6 Pre-commit hook (`gitleaks protect`)

**`.githooks/pre-commit`** — NEW:

```bash
#!/usr/bin/env bash
# HermesProof pre-commit: block commits that introduce secrets

set -e

if ! command -v gitleaks &>/dev/null; then
  echo "[pre-commit] gitleaks not installed; skipping secret-scan (install via go install or brew)" >&2
  exit 0
fi

gitleaks protect --staged --redact --no-banner --config .gitleaks.toml
```

Make executable: `chmod +x .githooks/pre-commit` and document in `docs/MAINTENANCE.md` how users install it: `git config core.hooksPath .githooks`.

`scripts/wizard.mjs` — add a wizard step that asks "Install pre-commit hook for secret scanning? [Y/n]" and runs the `git config` line if yes.

### 5.7 README + tool reference

**`README.md`** — bump truth-gates count from 17 to 24 (17 existing + 7 new = 24 truth gates).

**Important — gates ≠ tools:** the existing README shows two separate counts that get confused easily:
- "Truth gates" — the CI verification suite (currently 17, becoming 24 after this PR)
- "MCP tools" — the server's tool surface (currently 24; UNCHANGED by this PR)

After v0.6 lands, both counts coincidentally equal 24. They are NOT the same metric — keep them in separate badges and separate prose. Don't write "24 gates and 24 tools = 24" or any equality claim. The truth-gates table needs the 7 new rows; the MCP-tools section is untouched.

**`docs/TOOL_REFERENCE.md`** — add a "Truth gate inventory" section listing all 24 gates with one-line descriptions.

**`package.json`** — bump version `0.5.0` → `0.6.0`.

---

## 6. Tests

Add to `scripts/coordination-smoke-test.mjs`:

- `secret.scan rejects a synthetic Anthropic key in a tracked file`
- `secret.scan allowlist passes the .env.example synthetic placeholders`
- `auto-lint.check runs and emits SARIF`
- `agentic-test.coverage-audit fails when coverage drops below threshold`
- `HERMES3D_ENV_FILE resolution prefers env var over local .env`
- `HERMES3D_VPS_ENV_FILE only resolves when --vps-mode arg present`
- `pre-commit hook blocks staging of a synthetic secret`

All tests must pass on Windows + Linux (HermesProof's existing matrix). If `gitleaks` / `auto_linter` / `agentic-testing` aren't installed in CI, gate the tests on `command -v` checks and skip with a clear "tool not installed" message; don't fail.

---

## 7. Gates

```text
hermes_run_gate gateId=git-status      cwd=.
hermes_run_gate gateId=git-diff-check  cwd=.
```

Local validation:
- `npm install` (with the new `dotenv` dep added)
- `npm test` — all existing 47+ tests + new ones pass
- `npm run truth-gates` — now reports 17→24 gates passing (or whatever the count actually is). All required gates green.
- `npm run truth-gates -- --ci` — CI subset green (some advisory gates may skip)
- `gitleaks detect --config .gitleaks.toml --no-git --redact` — scans clean against the working tree (allowlist must cover existing fixtures)
- `git diff --check` — no whitespace errors

---

## 8. PR + close-out

```bash
git push -u origin feat/cp-hermesproof-0.6-gate-pack
gh pr create --base main \
  --title "feat(0.6): Secret + Quality + Test gate pack — gitleaks + auto_linter + agentic-testing + HERMES3D_ENV_FILE" \
  --body "[mirror v0.5 PR body shape; Hermes evidence chain: PASS; Task: CP-HERMESPROOF-0.6; Gate run via hermes_run_gate]"
```

Close-out:

```text
hermes_append_evidence
  owner=codex-impl-05
  taskId=CP-HERMESPROOF-0.6
  kind=checkpoint
  summary=v0.6 gate pack opened in PR #N at SHA <commit>; <X> gates total; secret.scan + auto-lint + agentic-test integrated.

hermes_release_files  owner=codex-impl-05  files=[the lock list]
hermes_release_task   owner=codex-impl-05  taskId=CP-HERMESPROOF-0.6
```

---

## 9. Hard rules

- DO NOT add any actual API keys, real or test, to any file. Synthetic keys for tests must match the `sk-ant-test-...` prefix that the gitleaks allowlist exempts.
- DO NOT skip the secret.scan gate if `gitleaks` isn't installed in CI — install it via the official action.
- DO NOT commit any file from `G:\private\` or `C:\Users\Admin\Downloads\VPS\` even if a script or test seems to require it.
- DO NOT add `auto_linter` or `agentic-testing` as runtime dependencies (they're dev/test tools only).
- DO NOT touch any file outside the §4 lock list.
- If `Ghenghis/auto_linter` or `Ghenghis/agentic-testing` isn't installable (no published package), write a blocked-handoff and skip — DO NOT manually `git clone` the repo into `node_modules`.

## 10. Failure protocol

If `auto_linter` or `agentic-testing` aren't installable as packages, write `handoffs/HANDOFF_TO_CLAUDE_CP-HERMESPROOF-0.6_BLOCKED.md` quoting the exact failure mode. The architect can either:

- Provide a path-fix (e.g., "use a stub for now, real integration in v0.6.1")
- Authorize partial scope (e.g., "ship just the secret.scan gate + .gitignore + pre-commit hook; defer auto_linter / agentic-testing to v0.6.1")

If gitleaks itself is missing from CI runners' default image, install it via `gitleaks/gitleaks-action@<sha>`. Don't fail the PR over tool installation.
