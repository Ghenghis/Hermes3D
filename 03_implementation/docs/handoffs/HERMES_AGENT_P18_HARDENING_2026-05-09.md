# Hermes Agent — P1-8 Post-Promotion Hardening (2026-05-09)

Branch: `claude/p18-post-promotion-hardening`
Lock owner: `claude-lead-p18-hardening`
Task ID: `P18-HARDENING-2026-05-09`

## Context

Wave 1 promoted Hermes Agent v0.13 (`v2026.5.7` "Tenacity Release") from
canary to default in PR #160. Adversarial review P1-8 surfaced four
findings on the post-promotion code surface in
`03_implementation/src/hermes3d/api/routes/agent_updates.py`:

| # | ID | Title | Severity | Status |
|---|----|-------|----------|--------|
| 1 | F1 | Cross-version backup pollution in `rollback_update` | P1 | shipped |
| 2 | F2 | (designed-only per brief; out of this PR's scope) | P1 | deferred (designed) |
| 3 | F3 | Local `SECRET_RE` bypass / consolidation into `redact_text` | P2 | DEFERRED — see "F3 deferral" below |
| 4 | F4 | `DEFAULT_CHECKOUT` literal still pointing at v0.12 | P3 | shipped |

Two of the four (F1, F4) ship in this PR. F2 is out-of-scope per brief.
F3 is deferred with rationale below — `gateways.redact_text` is
materially weaker than the local `SECRET_RE` for the
`[A-Za-z0-9_]*KEY=` shape, so swapping wholesale would be a regression.

## Shipped fixes

### F4 — alias realignment (low risk)

`agent_updates.DEFAULT_CHECKOUT` was a stale literal pointing at
`G:/Github/hermes-agent-fresh` (v0.12). After Wave 1 the resolver
default is `G:/Github/hermes-agent-v013-canary` (v0.13).

Change:
```python
# was:
DEFAULT_CHECKOUT = Path(os.environ.get("HERMES_AGENT_CHECKOUT", "G:/Github/hermes-agent-fresh"))
# now:
DEFAULT_CHECKOUT = DEFAULT_AGENT_CHECKOUT
```

`_repo_path()` already calls the per-call resolver (PR #155), so live
`HERMES_AGENT_CHECKOUT` flips remain unaffected. The alias is retained
for any back-compat consumer that imports the constant.

### F1 — cross-version backup safety (the consequential one)

**Hazard.** Operator flips `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`
mid-process to revert to v0.12. Calls `POST /api/agents/update/rollback`
(no `backup_id`). Pre-fix `_latest_backup()` returned the most-recent
backup globally — taken under v0.13 — and the route would `git checkout`
a v0.13 tag/commit into the v0.12 working tree. Result: corruption or 502.

**Fix surface (3 hunks).**

A. `_create_backup` adds a per-checkout disambiguator:
   - New helper `_checkout_path_hash(repo)` returns the 8-char SHA-256
     prefix of `str(repo)`.
   - `backup_id = f"{stamp}_{path_hash}_{safe_tag}_{commit}"`.
   - `metadata["checkout_path_hash"]` is persisted alongside the
     existing `metadata["checkout_path"]`.

B. `_latest_backup(checkout_path: Path | None = None)`:
   - When `checkout_path` is None: legacy "newest first wins" preserved.
   - When supplied: only backups whose `metadata["checkout_path"]`
     equals `str(checkout_path)` are considered. Legacy backups
     missing the field are EXCLUDED — they are untrustworthy across
     versions.

C. `rollback_update`:
   - Implicit (no `backup_id`): `_latest_backup(checkout_path=current)`,
     HTTP 409 with operator-clear detail when no match.
   - Explicit (`backup_id` supplied): cross-checks the backup's
     recorded `checkout_path` against the active one and refuses with
     HTTP 409 on mismatch. Legacy backups (no `checkout_path`) are
     still honored on explicit reference for runbook back-compat.

## Tests

- `04_testing/pytest/unit/test_agent_checkout_resolver.py`:
  +1 test (`test_agent_updates_default_checkout_aligned_to_resolver`).
  All 13/13 in this file now pass.
- `04_testing/pytest/unit/test_agent_updates_cross_version_rollback.py`
  (new): 9 tests covering the path-hash, the filter behavior, and the
  rollback refusal flow. All 9/9 pass.
- Existing agent_updates tests (auto_repair / config_redaction / meta /
  skip_path / ssrf / zip_dirty): 43/43 still pass — no regressions.

Pre-push hook (`scripts/precommit-fast.sh`) ran 39 unit tests + ruff +
forbidden-pattern scan. All passed.

## F3 deferral rationale

**Local `SECRET_RE` (in `agent_updates.py`):**
```python
SECRET_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+|([?&](?:token|key|api_key|access_token)=)[^&\s]+|([A-Za-z0-9_]*KEY=)[^\s]+")
```

Catches:
- `Bearer <token>` (any chars in `[A-Za-z0-9._~+/=-]`)
- URL query: `?token=` / `&access_token=` / `?key=` / `?api_key=`
- ALLCAPS-prefix: `API_KEY=...`, `MY_SECRET_KEY=...`, `KEY=...`

**`gateways.redaction.redact_text`:**

Catches Bearer JWTs, `sk-ant-*`, `sk-*` (OpenAI-shape), URL-with-secret
queries, `Authorization:` / `X-Api-Key:` headers, JSON secret-field
values, base64 blobs >=80 chars, long opaque tokens >=257 chars, etc.

**Coverage gap (verified empirically, 2026-05-09):**

```python
>>> redact_text("API_KEY=topsecretvalue123")
'API_KEY=topsecretvalue123'   # NO redaction
```

The local `SECRET_RE` redacts this; `redact_text` does not. The brief
explicitly says: "If `redact_text` is materially weaker than the local
SECRET_RE, REPORT and DO NOT ship F3 — file as a separate finding."

**Recommendation.** Before shipping F3:
1. Extend `gateways/redaction.py` with a generic `[A-Za-z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)=...` matcher (or equivalent).
2. Confirm parity by porting all 6 P1-8-listed shapes to a property
   test against `redact_text`.
3. THEN replace the local `SECRET_RE` in `agent_updates.py` (and the
   five sister sites: `agents.py`, `desktop_updates.py`,
   `desktop_compat.py`, `modules.py`, plus the `module_runtime.py`
   variant). Currently 6 sites duplicate the regex; consolidating
   without a stronger central redactor would be a regression.

Suggested next agent: `claude-redaction-consolidation` or any agent
holding the `gateways/redaction.py` lock.

## Persistence rule report

No findings ended unresolved with a "next agent should pick up".
F3 is reported above with the exact failing redaction, the module
involved, the remediation path, and the next agent to take it.

## Lock release

Locks acquired at start: 4 files (agent_updates.py, agent_checkout.py,
redaction.py, test_agent_checkout_resolver.py) under
`claude-lead-p18-hardening`. Released at the end of this PR's work.
See lock release confirmation in the parent agent's report.

## File-by-file summary

| File | Lines changed | Purpose |
|------|---------------|---------|
| `03_implementation/src/hermes3d/api/routes/agent_updates.py` | +69 / −5 | F1 + F4 |
| `04_testing/pytest/unit/test_agent_checkout_resolver.py` | +18 / 0 | F4 pin |
| `04_testing/pytest/unit/test_agent_updates_cross_version_rollback.py` | +325 (new) | F1 pins |

Total: 3 files, ~410 LoC including the new test file.

## Hermes evidence chain

- `Hermes evidence chain: PASS`
- `Task ID: P18-HARDENING-2026-05-09`
- `hermes_run_gate: pytest passes locally on Windows (resolver +
  cross-version suites = 22/22; existing agent_updates suites = 43/43;
  pre-push hook 39/39).`
