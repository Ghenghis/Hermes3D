"""BLK-021 cold-start race: GET /api/agents/update/status on a brand-new
process must return 200, not 500.

Background
----------
W5-3 GUI E2E drill discovered that the first ``/api/agents/update/status``
call after a fresh worker spawn returned 500 (DB schema not yet migrated /
mid-init); a second call returned 200 because by then ``init_db()`` had
finished. Existing API tests pass because they hit the API after warmup.

This integration test reproduces the race by spawning a brand-new Python
process per iteration via ``multiprocessing.get_context("spawn")``, which
guarantees no state bleed from earlier iterations (no inherited module
state, no cached ``_initialized`` flag, no warm SQLite page cache).

Each child process:
1. Points ``DB_PATH`` at an empty tempdir (so ``init_db`` truly runs from
   scratch).
2. Constructs the GUI FastAPI app via ``create_gui_app()``.
3. Issues a TestClient request to ``GET /api/agents/update/status``
   IMMEDIATELY — no warmup, no extra waits.
4. Returns the HTTP status code to the parent process.

The fix (db/init.py + api/app.py) makes ``init_db()`` synchronous at
factory time and thread-safe via ``_INIT_LOCK``. With the fix, all 5
fresh processes return 200; without it, at least one returns 500 with
"no such table: proof_events" or similar.
"""

from __future__ import annotations

import multiprocessing
import sys
from multiprocessing.connection import Connection
from pathlib import Path

import pytest

# Ensure src is on path for the parent process; child processes set it
# themselves below because multiprocessing 'spawn' starts a clean Python.
SRC = Path(__file__).resolve().parents[3] / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


COLD_START_RACE_ITERATIONS = 5


def _coldstart_status_call(pipe: Connection, repo_root: str, src_path: str, db_dir: str) -> None:
    """Run inside a fresh ``multiprocessing.spawn`` child.

    Hits ``/api/roadmap/status`` once, immediately, on a freshly
    constructed app whose DB lives at a brand-new path. The parent reads
    the resulting status code via ``pipe``.

    Why ``/api/roadmap/status`` and not ``/api/agents/update/status``:
    the agent-update status route makes outbound GitHub Releases API
    calls and can fail with 502/403 due to rate limiting under cold-start
    test conditions (5 fresh processes hitting api.github.com in 30s
    exceeds the unauthenticated rate limit). BLK-021 is the DB-init race;
    the GitHub network race is a separate concern. ``roadmap/status`` is
    a pure DB read (``SELECT * FROM roadmap_items``) — its only failure
    mode under cold start is the very race we are fixing.
    """
    # Re-initialize sys.path because spawn starts a clean interpreter.
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # Pin the DB to a per-process tempdir so we get a true cold start
    # (no leftover hermes3d.db from a previous run).
    from hermes3d.db import init as db_init  # noqa: E402

    db_init.DB_PATH = Path(db_dir) / "hermes3d.db"
    db_init.reset_initialization_state()  # clear any inherited flag

    try:
        # Importing app.py triggers create_gui_app() at module import.
        # With the BLK-021 fix this synchronously initializes the schema
        # BEFORE any router is wired, so the immediate request below
        # cannot race uncreated tables.
        from fastapi.testclient import TestClient  # type: ignore[import-not-found]

        from hermes3d.api.app import create_gui_app  # noqa: E402

        app = create_gui_app()
        with TestClient(app) as client:
            # IMMEDIATE: no warmup request, no sleep, no setup.
            resp = client.get("/api/roadmap/status")
            pipe.send(("status_code", resp.status_code, resp.text[:200]))
    except Exception as exc:  # noqa: BLE001 — surface any error to parent
        pipe.send(("error", repr(exc), ""))
    finally:
        pipe.close()


@pytest.mark.integration
def test_blk021_coldstart_no_race(tmp_path: Path) -> None:
    """Spawn 5 fresh processes; each MUST return 200 on the first call."""
    repo_root = str(Path(__file__).resolve().parents[3])
    src_path = str(SRC)

    ctx = multiprocessing.get_context("spawn")
    results: list[tuple[str, int | str, str]] = []

    for i in range(COLD_START_RACE_ITERATIONS):
        db_dir = tmp_path / f"iter_{i}"
        db_dir.mkdir(parents=True, exist_ok=True)
        parent_conn, child_conn = ctx.Pipe(duplex=False)
        proc = ctx.Process(
            target=_coldstart_status_call,
            args=(child_conn, repo_root, src_path, str(db_dir)),
        )
        proc.start()
        # Generous timeout: child does FastAPI app construction + 1 HTTP call.
        proc.join(timeout=60)
        assert not proc.is_alive(), f"iter {i}: child still alive after 60s"
        if parent_conn.poll(timeout=5):
            results.append(parent_conn.recv())
        else:
            results.append(("timeout", -1, "no message from child"))
        parent_conn.close()
        proc.close()

    # Every iteration MUST be ("status_code", 200, ...) for the fix to be
    # considered to address BLK-021.
    failures: list[str] = []
    for i, (kind, value, body) in enumerate(results):
        if kind != "status_code":
            failures.append(f"iter {i}: child errored: {kind} {value} {body}")
        elif value != 200:
            failures.append(f"iter {i}: status={value} body={body}")
    assert not failures, "BLK-021 race re-surfaced:\n" + "\n".join(failures)


def _coldstart_concurrent_calls(pipe: Connection, src_path: str, db_dir: str) -> None:
    """Same shape as ``_coldstart_status_call`` but fires 8 concurrent
    first-requests against a single fresh app to stress the init lock.

    Targets ``/api/roadmap/status`` which is a pure DB read (no outbound
    HTTPS) so any non-200 is unambiguously a DB-init race rather than a
    transient GitHub API hiccup.
    """
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from concurrent.futures import ThreadPoolExecutor

    from hermes3d.db import init as db_init  # noqa: E402

    db_init.DB_PATH = Path(db_dir) / "hermes3d.db"
    db_init.reset_initialization_state()

    try:
        from fastapi.testclient import TestClient  # type: ignore[import-not-found]

        from hermes3d.api.app import create_gui_app  # noqa: E402

        app = create_gui_app()
        codes: list[int] = []
        with TestClient(app) as client:
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [
                    pool.submit(client.get, "/api/roadmap/status")
                    for _ in range(8)
                ]
                for fut in futures:
                    codes.append(fut.result().status_code)
        pipe.send(("status_codes", codes, ""))
    except Exception as exc:  # noqa: BLE001
        pipe.send(("error", repr(exc), ""))
    finally:
        pipe.close()


@pytest.mark.integration
def test_blk021_coldstart_concurrent_first_requests(tmp_path: Path) -> None:
    """8 concurrent first requests against ONE fresh app must all return 200.

    Stresses the ``_INIT_LOCK`` defense-in-depth path even when the factory-
    level synchronous ``init_db()`` is bypassed in some future refactor.
    Uses ``/api/roadmap/status`` (pure DB read) to isolate DB-init races
    from network flakiness.
    """
    src_path = str(SRC)
    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(
        target=_coldstart_concurrent_calls,
        args=(child_conn, src_path, str(tmp_path)),
    )
    proc.start()
    proc.join(timeout=60)
    assert not proc.is_alive(), "child still alive after 60s"
    assert parent_conn.poll(timeout=5), "no message from child"
    kind, value, body = parent_conn.recv()
    parent_conn.close()
    proc.close()

    assert kind == "status_codes", f"child errored: {kind} {value} {body}"
    bad = [c for c in value if c != 200]
    assert not bad, f"BLK-021 concurrent race re-surfaced: codes={value}"
