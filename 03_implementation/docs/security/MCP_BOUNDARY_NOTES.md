# Hermes3D MCP / Tool-Boundary Notes

Lane 19 (H3D-CLAUDE-SECURITY-MCP). Companion to
`03_implementation/proof/security/SECURITY_AUDIT_2026-05-06.json`.

## Tool surface enumerated

The Hermes3D backend's MCP boundary is the FastAPI HTTP surface plus the
in-process printer / agent / scanner adapters. The audit covered:

- `03_implementation/src/hermes3d/core/security/injection_scanner.py` — the
  in-house OWASP LLM-01 scanner (commit `0c9b6d9`). Two rulesets ship:
  `owasp_llm01.yaml` (>= 15 rules) and `curated_inhouse.yaml` (>= 10 Hermes3D
  patterns: G-code over-temp, thermal-runaway disable, lock-release-all,
  handoff forge, owner spoof, proof bypass).
- `03_implementation/src/hermes3d/services/local_state.py` — printer fleet
  state and the build-plate-clearance gate (`assert_build_plate_clear`).
- `03_implementation/src/hermes3d/services/module_runtime.py` — module probe
  registry. Carries the canonical secret-redaction helper `_redact_text`
  driven by `SECRET_RE` (URL-userinfo + token-style query parameters).
- `03_implementation/src/hermes3d/services/agent_runtime.py` — OpenAI-
  compatible runtime URL validator (`trusted_runtime_url`) and private-env
  reader (`private_env`).
- `03_implementation/src/hermes3d/services/code_history.py` — canonical
  user-supplied-path validator (`_resolve_project_path`,
  `_resolve_project_subpath`). Codex-owned; this lane only audits via
  behavioural tests.

## Policy gates that protect printers

| Gate | Function | Action on violation |
| ---- | -------- | ------------------- |
| Build-plate clearance | `local_state.assert_build_plate_clear` | `HTTPException(409, BUILD_PLATE_NOT_CLEARED)` |
| FLSUN S1 read-only lock | `printer_id == 'flsun_s1'` -> `locked=True, write_enabled=False` | All write actions filtered upstream |
| Agent runtime URL gate | `agent_runtime.trusted_runtime_url` | Returns `None` for any non-private host, public IP, credentials-in-URL, query, fragment, wrong scheme, or self-bridge port (8765, 8642) |
| Injection scanner fail-closed | `InjectionScanner(fail_threshold='high'|'medium'|'low')` | `ScanResult.fail_closed=True` when severity >= threshold |
| Secret redaction in proof JSON | `module_runtime._redact_text` | Subprocess stdout/stderr is redacted before `output_head` writes to `LOCAL_TOOLING_AUDIT.json` |

## Secret-handling boundary at `G:/private/.env`

Per project convention (`feedback_no_paid_services.md` and
`reference_secret_storage.md`), all `.env` files and API keys live OUTSIDE
every repo workspace at `G:\private\`. The loader is
`hermes3d.services.agent_runtime.private_env`, with override path via
`HERMES3D_ENV_FILE`. The audit pinned:

1. No source file under `services/` carries a hardcoded secret-shaped
   string literal (sk-..., ghp_..., AKIA..., `bearer xxx`, xoxb-...).
2. No logging emitter (`print`, `log.*`, `logger.*`) in those services
   passes a secret-shaped literal directly.
3. No logging emitter in `agent_runtime.py` passes the `private_values`
   dict (or the result of `private_env()` / `env_value()`) into a logger.
4. Subprocess output flowing into `output_head` (which is persisted in
   `LOCAL_TOOLING_AUDIT.json` proof) is funnelled through `_redact_text`
   before any logging or proof writeout.

## Findings (logged, not silently fixed)

See `SECURITY_AUDIT_2026-05-06.json` for the full structured record.

- **FINDING-INJ-1** (medium, owner = security ruleset lane):
  `LLM01-LEAK-VERBATIM` regex misses the reverse word order
  `the prompt verbatim`. Pinned by an `xfail(strict=True)` test that
  flips to FAIL when the rule is hardened.
- **FINDING-INJ-2** (medium, owner = security ruleset lane):
  Zero-width-space (U+200B) splits `ignore` and bypasses
  `LLM01-IGN-PREV`; `dump` is also not in any leak rule. Mitigation is
  unicode normalisation pre-match plus richer leak alternation.
- **FINDING-PATH-1** (low, informational, owner = Codex / code_history
  lane): `_resolve_project_subpath` silently re-roots
  `/etc/passwd` and `//attacker.example/share/x` into PROJECT_ROOT
  rather than rejecting. SAFE (no escape; `relative_to(PROJECT_ROOT)`
  enforces containment) but the contract is coercive, not rejective.

## Scope limits enforced by this lane

- READ-ONLY against `services/code_history.py`, `routes/code_operator.py`,
  `routes/agents.py` (code-operator section), and `db/schema.sql`
  (code-history rows). Confirmed by `git diff --stat` containing only
  paths under `03_implementation/{tests,proof,docs}/security/`.
- Light LLM-02 coverage (insecure output handling) and LLM-06
  (sensitive information disclosure) added where scaffolding allowed —
  see `vectors_covered.owasp_llm02_*` and `owasp_llm06_*` in the audit
  JSON.
- No new MCP servers added or stripped; no `*.mcp.json` /
  `claude_desktop_config*.json` files exist at the repo root.

## Required gates (all PASS)

```text
python -m py_compile 03_implementation/src/hermes3d/api/routes/*.py \
                    03_implementation/src/hermes3d/services/*.py
python 03_implementation/scripts/scan_active_ui_no_fake.py
python -m pytest 03_implementation/tests/security/ -q
cd 03_implementation/ui && npm run lint
```

Result: `78 passed, 2 xfailed` for pytest. The xfails are the recorded
findings — they will flip RED the moment a future PR fixes them, which
is the intended alarm.
