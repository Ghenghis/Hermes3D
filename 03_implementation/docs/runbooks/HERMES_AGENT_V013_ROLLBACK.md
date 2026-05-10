# Hermes Agent v0.13 -> v0.12 Rollback Runbook

> **Audience:** on-call operators of the Hermes3D OS FastAPI process.
> **Goal:** flip the active Hermes Agent checkout from v0.13 (post Wave 1
> default) back to v0.12 in **under 60 seconds** without restarting the
> server, with the option to escalate to a PR-level revert if the
> resolver-flip is not enough.
> **Audit:** every step records to `proof_events` and `agent_config`;
> the doctrine is 12-Factor App Rule III (config in env vars, "easy to
> change between deploys without changing any code"
> [12factor.net/config](https://12factor.net/config)).

| Field           | v0.13 (current default)               | v0.12 (rollback target)         |
|-----------------|---------------------------------------|---------------------------------|
| Tag             | v2026.5.7 ("Tenacity Release")        | v2026.4.30                      |
| Checkout path   | `G:/Github/hermes-agent-v013-canary`  | `G:/Github/hermes-agent-fresh`  |
| HEAD (verified) | `498bfc7`                             | `73bf3ab1`                      |
| Promoted via    | PR #160 squash `3158a4e`              | (was the prior default)         |
| Per-call resolver | PR #155 `8544bbc`                   | PR #155 `8544bbc`               |

The resolver lives in
[`03_implementation/src/hermes3d/services/agent_checkout.py`](../../src/hermes3d/services/agent_checkout.py)
and reads `HERMES_AGENT_CHECKOUT` **on every call** (not at module
import). That is the property that makes a 60-second mid-process flip
possible — see Section 2.

---

## Section 1 — When to use this runbook

Use this runbook when **any** of the following symptoms are observed in
production after the v0.13 promotion (PR #160 / `3158a4e`):

1. **Provider 5xx storms.** v0.13 sends a request format that the
   currently-deployed model providers reject (HTTP 5xx, repeated
   `provider_unavailable` events in `proof_events`). Confirm via:

   ```sql
   SELECT COUNT(*) FROM proof_events
    WHERE event_type LIKE 'provider_%error%'
      AND created_at >= datetime('now', '-15 minutes');
   ```

2. **Runtime crash on the canary path.** Uncaught exceptions in
   `hermes-agent-v013-canary` reach the FastAPI worker (look for
   `ERROR uvicorn.error` lines or `proof_events.event_type =
   hermes_agent_runtime_crash`).

3. **Security regression.** A v0.13-only code path leaks PII / secrets
   that the v0.12 redactor caught. Confirm by sampling
   `proof_events.payload` for fields that should be `<redacted>` but
   are not.

4. **Bounded-CLI sandbox escape suspicion.** Unexpected processes spawn
   from the Hermes Agent runner despite the BLK-013 hardening
   (`--network=none --read-only --cap-drop=ALL`). This is high-severity
   and warrants the heavier PR-level revert in Section 5 in addition to
   the env flip.

5. **Outdated provider auth.** v0.13's provider plugin requires a
   header / scope your tenant has not provisioned yet, and v0.12's
   simpler `Authorization: Bearer <token>` flow still works.

If the symptom does **not** match one of the above, this runbook is not
the right tool — open an incident ticket and triage instead. Rolling
back is non-destructive, but it does drop access to v0.13-only features
(e.g. the Tenacity recovery loop hooks shipped upstream as PR #21193).

---

## Section 2 — Mid-process flip (no restart, target <60s)

> **Doctrine.** The 12-Factor App principle on Config states that env
> vars are "easy to change between deploys without changing any code"
> ([12factor.net/config](https://12factor.net/config)). The Wave A5
> resolver (PR #155) implements that contract by reading
> `HERMES_AGENT_CHECKOUT` per call, so changing the env var while the
> process is alive is sufficient — no restart, no code change.

The single env-var flip is:

```text
HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh
```

How you set it depends on how the FastAPI process is hosted. The four
canonical hosting modes follow. If your host is none of these, see
**Section 2.5** (alternatives for blocked hosts).

### 2.1 Windows Service (`sc.exe` + `nssm` style)

The Windows Service Control Manager reads the service's environment
once **at process start**, but you can set the env var on the running
process via PowerShell + the service's PID. Two paths:

- **Inline (no restart needed):** PowerShell can set an env var on a
  running process only by re-launching it, which defeats the goal.
  Instead, open the service-owner shell that already runs the
  uvicorn worker and update its env via the service config tool of
  your choice. For NSSM-managed services:

  ```powershell
  # Set the new value on the service config
  & "C:\Program Files\nssm\nssm.exe" set Hermes3DOS AppEnvironmentExtra `
      "HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh"
  ```

  This persists the value but does **not** propagate to the running
  worker. To get a no-restart flip, use option (b).

- **(b) IPC/admin endpoint flip (recommended on Windows):** the
  FastAPI process exposes the resolver to itself via
  `os.environ`. Use a one-shot admin script that runs in-process
  via uvicorn's import path (or call an internal admin endpoint if
  one is wired) to do `os.environ["HERMES_AGENT_CHECKOUT"] =
  "G:/Github/hermes-agent-fresh"`. The next request that hits any
  route calling `_repo_path()` (e.g.
  `GET /api/agents/update/status`) reads the new value live.

  If no admin endpoint exists yet, fall back to a brief restart with
  the new `nssm` value already persisted:

  ```powershell
  & "C:\Program Files\nssm\nssm.exe" restart Hermes3DOS
  ```

  Restart cost is ~3–6 s on a warm machine; still well inside the
  60-second budget.

### 2.2 systemd unit (Linux production hosts)

systemd reads `Environment=` and `EnvironmentFile=` directives at
unit start; new values do **not** propagate to a running process via
`systemctl reload`. The supported flow is edit-then-restart:

```bash
# /etc/systemd/system/hermes3d-os.service.d/override.conf (drop-in)
[Service]
Environment=HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh
```

Apply:

```bash
sudo systemctl daemon-reload
sudo systemctl restart hermes3d-os.service
```

A restart on a warm host completes in ~2–4 s. If you need a true
zero-restart flip on Linux, use the same in-process technique
described in **2.1(b)**.

### 2.3 Docker / docker-compose

Per Docker docs ([docker run reference](https://docs.docker.com/reference/cli/docker/container/run/#env)),
`-e`/`--env` and `--env-file` are evaluated at **container creation**,
so an existing container's env is immutable. The supported flow is
recreate-the-container with the new value:

```bash
docker run -d --name hermes3d-os \
    -e HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh \
    -e <other-existing-vars> \
    hermes3d-os:latest
```

Or, with `compose`:

```yaml
# docker-compose.override.yml
services:
  hermes3d-os:
    environment:
      HERMES_AGENT_CHECKOUT: "G:/Github/hermes-agent-fresh"
```

```bash
docker compose up -d hermes3d-os    # recreates with new env
```

Container recreation takes ~5–15 s including health-probe stabilization.

### 2.4 Bare uvicorn with `--env-file`

For development / single-host deployments the FastAPI process is
launched with:

```bash
uvicorn hermes3d.api.app:app --host 0.0.0.0 --port 8000 \
    --env-file /etc/hermes3d/hermes-agent.env
```

**Important:** `uvicorn --reload` is documented as a development-only
feature ("you **shouldn't** use it in **production**", per
[fastapi.tiangolo.com/deployment/manually](https://fastapi.tiangolo.com/deployment/manually/)),
so do not rely on `--reload` to pick up env-file changes in prod.

Edit the env file and restart uvicorn:

```bash
# 1. Edit the env file (no secrets — just the path flip)
sed -i 's|^HERMES_AGENT_CHECKOUT=.*|HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh|' \
    /etc/hermes3d/hermes-agent.env
# 2. Send SIGTERM to uvicorn and let your supervisor (systemd / pm2 /
#    supervisord) restart it with the new env-file values
kill -TERM "$(pgrep -f 'uvicorn hermes3d.api.app:app')"
```

### 2.5 If your host blocks every option above

Fall back to the **PR-level revert** (Section 5). It is heavier (CI
gate + merge), but it is host-agnostic and changes the resolver
default itself, so even processes that cannot read a new env var pick
up v0.12 on next start.

---

## Section 3 — Verification (3 commands)

After the flip lands, run all three. Treat any FAIL as "rollback not
yet live — investigate before declaring success."

```bash
# 1. The status endpoint reflects the v0.12 path.
curl -fsS http://localhost:8000/api/agents/update/status | \
    python -m json.tool | grep -E '"checkout_path"|"exact_tag"|"commit"'
# Expected: "checkout_path": "G:/Github/hermes-agent-fresh"
#           "exact_tag":     "v2026.4.30"     (or "nearest_tag")
#           "commit":        "73bf3ab1xxxx"   (12-char short SHA)

# 2. The resolver itself returns the v0.12 path live.
python -c "from hermes3d.services.agent_checkout import hermes_agent_checkout; print(hermes_agent_checkout())"
# Expected: G:\Github\hermes-agent-fresh    (Windows)
#       OR  G:/Github/hermes-agent-fresh    (Unix-style)

# 3. The checkout itself is at the expected v0.12 commit and clean.
git -C G:/Github/hermes-agent-fresh rev-parse HEAD
git -C G:/Github/hermes-agent-fresh status --porcelain
# Expected: 73bf3ab1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#           (no output for status --porcelain == clean tree)
```

If any of (1)/(2) still report `hermes-agent-v013-canary`, the env var
did not propagate to the running process — re-do Section 2 with a
restart, then re-verify.

---

## Section 4 — DB cleanup (tag, do not delete)

The v0.13 promotion run wrote rows into both `agent_config` and
`proof_events` (see
[`agent_updates.py`](../../src/hermes3d/api/routes/agent_updates.py),
search for `INSERT OR REPLACE INTO agent_config` and
`_append_proof_event`). After the rollback, those rows are stale but
**should not be deleted** — they are evidence-chain entries.

Tag them with a discriminator instead, and filter by `checkout_path` in
all post-rollback diagnostics:

```sql
-- (a) Inspect every v0.13 update/rollback record currently in
--     agent_config.
SELECT key, json_extract(value, '$.checkout_path') AS checkout_path,
       json_extract(value, '$.actor')              AS actor,
       updated_at
  FROM agent_config
 WHERE key LIKE 'hermes_agent.update.last_%'
 ORDER BY updated_at DESC;

-- (b) Same view from the proof_events ledger.
SELECT id, event_type, source_agent,
       json_extract(payload, '$.checkout_path') AS checkout_path,
       created_at
  FROM proof_events
 WHERE event_type LIKE 'hermes_agent_update_%'
   AND created_at >= datetime('now', '-24 hours')
 ORDER BY created_at DESC;

-- (c) Mark the v0.13 entries as superseded by the rollback. Do NOT
--     delete; the proof chain must remain intact.
UPDATE agent_config
   SET value = json_set(value, '$.superseded_by_rollback',
                        json_object(
                          'rolled_back_to', 'G:/Github/hermes-agent-fresh',
                          'rolled_back_at', datetime('now'),
                          'reason',         'see incident ticket'
                        ))
 WHERE key LIKE 'hermes_agent.update.last_%'
   AND json_extract(value, '$.checkout_path') = 'G:/Github/hermes-agent-v013-canary';

-- (d) Append a proof_events entry that the rollback has happened.
INSERT INTO proof_events (id, event_type, source_agent, payload)
VALUES (
    lower(hex(randomblob(16))),
    'hermes_agent_rollback_completed',
    'hermes3d-operator',
    json_object(
      'from_checkout', 'G:/Github/hermes-agent-v013-canary',
      'to_checkout',   'G:/Github/hermes-agent-fresh',
      'from_tag',      'v2026.5.7',
      'to_tag',        'v2026.4.30',
      'mechanism',     'env_flip_no_restart'   -- or 'pr_revert'
    )
);
```

Operators **must run (d)** so the evidence chain has a single source of
truth for "this rollback happened at <timestamp>." Skipping it is a
weakness — see standing instruction `feedback_weakness_correction.md`.

---

## Section 5 — PR-level revert (heavier nuclear option)

If the env flip is not enough — e.g. the v0.13 path is being hit
through a code path that bypasses `hermes_agent_checkout()`, or the
resolver default itself was depended upon by another module — escalate
to reverting PR #160:

```bash
# Branch off the canonical integration branch
git fetch origin
git checkout -b hotfix/v013-rollback origin/feat/hermes3d-7-complete-gui-repo-wiring

# Revert the squash merge for PR #160 (mainline parent = -m 1)
git revert -m 1 3158a4e152350eefd8805015420ed5007629fb04

# Push and open the hotfix PR through the release gateway
#  (per 06_release/ROLLBACK_RUNBOOK.md the rollback/* prefix must be
#   renamed to hotfix/* to satisfy branch-guard.yml)
git push -u origin hotfix/v013-rollback
gh pr create --base feat/hermes3d-7-complete-gui-repo-wiring \
             --head hotfix/v013-rollback \
             --title "hotfix: revert v0.13 promotion (PR #160)" \
             --label "rollback,expedited" \
             --body  "Reverts 3158a4e (PR #160). Resolver default returns to v0.12 (G:/Github/hermes-agent-fresh)."
```

After merge:

1. Re-run the three verification commands in **Section 3** (the
   resolver default itself now points at v0.12, so the env var is no
   longer required).
2. Append a `proof_events` row of type `hermes_agent_rollback_completed`
   with `mechanism = 'pr_revert'`.

This path also restores a clean upgrade story for any future
re-promotion: revert + re-promote = clean diff.

---

## Section 6 — Re-promotion path (flip back to v0.13)

Once the v0.13 issue is fixed upstream / in our adapter:

1. **If you only used the env flip (Sections 2–4):** unset the env
   var. The resolver default is still v0.13.

   ```bash
   # systemd: remove the override.conf and daemon-reload + restart
   sudo rm /etc/systemd/system/hermes3d-os.service.d/override.conf
   sudo systemctl daemon-reload
   sudo systemctl restart hermes3d-os.service
   ```

   ```bash
   # docker: drop the env entry from compose and recreate
   docker compose up -d hermes3d-os
   ```

   ```powershell
   # Windows Service / NSSM
   & "C:\Program Files\nssm\nssm.exe" set Hermes3DOS AppEnvironmentExtra ""
   & "C:\Program Files\nssm\nssm.exe" restart Hermes3DOS
   ```

   Re-run Section 3's verification — `checkout_path` should be back to
   `G:/Github/hermes-agent-v013-canary` and `exact_tag` to `v2026.5.7`.

2. **If you used the PR-level revert (Section 5):** open a re-promotion
   PR that reverts the revert (a clean `git revert <revert-sha>`), or
   cherry-pick the original `3158a4e` onto a fresh branch. Run the
   Wave 1 hard-gate suite again before merge:

   - MiniMax + DeepSeek probes both `accepted=true`
   - Canary runtime smoke (8/8 imports, 38-subcommand CLI, 10 MCP
     tools, redaction default-ON)
   - v0.12 production checkout still bit-identical
   - Per-call resolver mid-process flip 4/4

3. **Append final evidence.** Whichever path you took, write one last
   `proof_events` row:

   ```sql
   INSERT INTO proof_events (id, event_type, source_agent, payload)
   VALUES (
       lower(hex(randomblob(16))),
       'hermes_agent_repromotion_completed',
       'hermes3d-operator',
       json_object(
         'mechanism',     'env_unset',  -- or 're_promote_pr'
         'incident_id',   '<from your ticket>',
         'completed_at',  datetime('now')
       )
   );
   ```

---

## References

- 12-Factor App, Rule III — Config: <https://12factor.net/config>
- Docker `run` env-var reference: <https://docs.docker.com/reference/cli/docker/container/run/#env>
- FastAPI deployment / uvicorn `--reload` warning: <https://fastapi.tiangolo.com/deployment/manually/>
- Repo: production rollback runbook (tag-based, complementary):
  [`06_release/ROLLBACK_RUNBOOK.md`](../../../06_release/ROLLBACK_RUNBOOK.md)
- Repo: per-call resolver implementation:
  [`03_implementation/src/hermes3d/services/agent_checkout.py`](../../src/hermes3d/services/agent_checkout.py)
- Repo: agent-update API + DB writes:
  [`03_implementation/src/hermes3d/api/routes/agent_updates.py`](../../src/hermes3d/api/routes/agent_updates.py)
- PR #160 (v0.13 promotion squash): commit `3158a4e152350eefd8805015420ed5007629fb04`
- PR #155 (per-call resolver): commit `8544bbc`

---

## Appendix A — One-page emergency card

Print this and tape it next to the on-call laptop.

```text
ROLLBACK v0.13 -> v0.12 (target <60s)

  1. Set env var on the FastAPI process:
       HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh
     (systemd: drop-in override + daemon-reload + restart)
     (docker:  -e on a recreated container)
     (uvicorn: edit --env-file + restart)

  2. Verify (all three must match):
       curl /api/agents/update/status            -> checkout_path = G:/Github/hermes-agent-fresh
       python -c "from hermes3d.services.agent_checkout import hermes_agent_checkout; print(hermes_agent_checkout())"
       git -C G:/Github/hermes-agent-fresh rev-parse HEAD   -> 73bf3ab1...

  3. INSERT one row into proof_events with
       event_type = 'hermes_agent_rollback_completed'.

  4. If env-flip insufficient: revert PR #160 (3158a4e) via
       git revert -m 1 3158a4e ... && gh pr create --label rollback,expedited

  5. Re-promotion: unset HERMES_AGENT_CHECKOUT and restart, OR
                   revert-the-revert PR.
```
