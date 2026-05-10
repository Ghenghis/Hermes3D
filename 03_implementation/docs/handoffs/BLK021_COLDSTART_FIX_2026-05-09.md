# BLK-021 Cold-Start Race Fix

**Date:** 2026-05-09
**Agent:** W8-11 (Claude)
**Branch:** `claude/w8-11-blk021-coldstart-fix`
**Hermes lock owner:** `claude-w8-11-blk021`
**Blocker registered by:** W5-3 (GUI E2E drill, see
`HERMES_AGENT_V013_GUI_E2E_2026-05-09.md` L137-138 and
`E2E_BLOCKER_REGISTRY_2026-05-09.md` row BLK-021)

---

## Symptom

The first `GET /api/agents/update/status` request after a fresh worker
spawn returned 500. A second call returned 200. Existing API tests pass
because they hit the API after warmup (e.g. through `TestClient`'s
`with` context which fires `startup` before the first test request).

## Root Cause

Two compounding facts:

1. `db/init.py:init_db()` was called from two places:
   - `api/app.py` `@app.on_event("startup")` hook (async, fired after
     uvicorn begins accepting requests).
   - `api/routes/_common.py:ensure_db()` lazily on every read/write.
2. Two concurrent first requests could each enter `init_db()`
   simultaneously. While `CREATE TABLE IF NOT EXISTS` is idempotent in
   isolation, the surrounding `_migrate()` (`ALTER TABLE`) and `_seed()`
   (`INSERT OR IGNORE` referencing tables another writer is mid-create)
   can fail with `no such table: proof_events` or `database is locked`
   before either commit lands.

The 500 surfaced from the very first call to `_append_proof_event(...)`
inside `update_status()` —
`INSERT INTO proof_events (...)` against an uncommitted schema.

## Fix (Option B + thread-safe guard)

Two-line strategy chosen explicitly because the project explicitly
avoids `tenacity` (see `core/orchestration/retry_controller.py` L11-13:
"Local-first. Pure stdlib means zero new deps."). Option A (retry
adapter) would either pull in a new dep or duplicate retry primitives.

### `03_implementation/src/hermes3d/db/init.py`

- Added module-level `_INIT_LOCK = threading.Lock()` and
  `_initialized: bool = False`.
- `init_db(*, force: bool = False) -> Path` is now idempotent and
  serialized: fast-path returns when `_initialized` is True; slow path
  acquires the lock, double-checks the flag, runs schema/migrate/seed,
  commits, then sets the flag.
- Added `reset_initialization_state()` — test-only helper for cases
  where tests swap `DB_PATH` to a tempdir.

### `03_implementation/src/hermes3d/api/app.py`

- `create_gui_app()` now calls `init_db()` **synchronously, BEFORE**
  any router is wired or any middleware registered. This guarantees
  the SQLite schema is fully created/migrated/seeded before the
  application can accept any HTTP request.
- The existing `@app.on_event("startup")` hook is retained as
  defense-in-depth for forked-worker scenarios (`multiprocessing.spawn`
  on Windows does not inherit module-level state from the parent).

### `04_testing/pytest/integration/test_blk021_coldstart_no_race.py`

Two new integration tests, both running inside fresh processes spawned
via `multiprocessing.get_context("spawn")` — guaranteeing no inherited
module state, no warm SQLite page cache, no leaked `_initialized` flag.

1. `test_blk021_coldstart_no_race` — spawns **5 fresh processes**,
   each pointing `DB_PATH` at a fresh tempdir, each immediately issuing
   `GET /api/roadmap/status` with no warmup. Asserts every call
   returns 200.
2. `test_blk021_coldstart_concurrent_first_requests` — single fresh
   process, 8 concurrent first requests via `ThreadPoolExecutor` against
   `GET /api/roadmap/status`, stresses `_INIT_LOCK` even if a future
   refactor bypasses the factory-level `init_db()`. Asserts all 8 return
   200.

Both tests are marked `@pytest.mark.integration`.

**Why `/api/roadmap/status` and not `/api/agents/update/status`:** the
agent-update status route makes outbound GitHub Releases API calls and
can fail with 502/403 due to rate limiting under cold-start test
conditions (observed: 5 fresh processes hitting `api.github.com` in 30s
exceed the unauthenticated rate limit and produce HTTP 403 / 502). BLK-021
is the DB-init race; the GitHub network failure is a separate concern.
`roadmap/status` is a pure DB read (`SELECT * FROM roadmap_items`) — its
only failure mode under cold start is the very race we are fixing.

### Why not Option A (retry adapter)

- Tenacity is not in `requirements.txt` / `requirements-dev.txt` /
  `pyproject.toml`.
- The project ships `core/orchestration/retry_controller.py` precisely
  to avoid the tenacity dep ("Why a custom controller (vs tenacity):
  zero new deps").
- A retry decorator does not address the underlying race — it only
  hides it behind a 100ms-500ms first-request latency penalty for every
  cold start, masking schema corruption that a future change could
  re-introduce.

## Sources

- FastAPI startup events:
  https://fastapi.tiangolo.com/advanced/events/
- SQLite concurrency / "database is locked" semantics:
  https://www.sqlite.org/lockingv3.html
- W5-3 receipt: see `HERMES_AGENT_V013_GUI_E2E_2026-05-09.md` lines
  137-138 (the W5-3 branch). Cited in `E2E_BLOCKER_REGISTRY_2026-05-09.md`
  row BLK-021.

## Test Receipt

```
$ python -m pytest 04_testing/pytest/integration/test_blk021_coldstart_no_race.py -v
04_testing\pytest\integration\test_blk021_coldstart_no_race.py ..       [100%]
============================= 2 passed in 25.03s ==============================
```

- `test_blk021_coldstart_no_race`: **5/5** fresh-process iterations
  returned 200.
- `test_blk021_coldstart_concurrent_first_requests`: **8/8** concurrent
  first requests returned 200.

## Files Changed

| File | LoC | Purpose |
|---|---|---|
| `03_implementation/src/hermes3d/db/init.py` | +50 / -5 | Thread-safe idempotent `init_db()` + `reset_initialization_state()` |
| `03_implementation/src/hermes3d/api/app.py` | +14 / -1 | Sync `init_db()` at factory time before router wiring |
| `04_testing/pytest/integration/test_blk021_coldstart_no_race.py` | +152 / 0 | Two fresh-process race tests |
| `03_implementation/docs/handoffs/BLK021_COLDSTART_FIX_2026-05-09.md` | +149 / 0 | This document |

## Constraints Honored

- No secrets, no `.env` writes — fix is pure-stdlib + threading.
- All edits made under Hermes MCP locks owned by `claude-w8-11-blk021`.
- No DB schema change — only init/race logic touched.
- Free / OSS only — zero new dependencies.

## Rollback

If the synchronous factory-time `init_db()` causes app construction to
exceed acceptable startup latency (currently ~150ms on a clean
tempdir), revert `api/app.py` to call `init_db()` only in the
`@app.on_event("startup")` hook. The `_INIT_LOCK` in `db/init.py`
alone is sufficient to prevent the race, but the factory-time call is
preferred because it removes the gap between "uvicorn accepts request"
and "startup hook completes."
