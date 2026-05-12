"""W21-A4 MVP-2 — background queue poller.

Started as an asyncio background task in :mod:`hermes3d.api.app`'s startup
hook. Every ``POLL_INTERVAL_SECS`` the poller:

  1. Reads the live Hermes Agent persona roster from the backend's agent
     registry (the same dict served by ``/api/agents/health``).
  2. Walks pending tasks in ``.hermes3d_orchestrator/tasks/pending/``.
  3. For each pending task, matches ``target_owner_pattern`` against the
     persona roster. The first matching, currently-idle persona claims
     the task.
  4. Heartbeats already-claimed-by-us tasks so the orchestrator does not
     consider them stale.

The poller NEVER:
  - executes the task content (that is MVP-3 surface)
  - moves a task to ``done/`` without an explicit operator action (the
    HTTP route ``/api/agents/queue/complete/{task_id}`` does that)
  - claims more than ``MAX_CLAIMS_PER_TICK`` per poll (rate-limit so a
    burst of pending tasks does not starve idle personas of fair share)

Lag-protection rules followed:
  - Interval is ``POLL_INTERVAL_SECS`` (15s default) — well over the
    sub-5s anti-pattern and well under the 60s normal-action budget.
  - Each tick's work is bounded: list pending once, decide once, claim
    up to MAX_CLAIMS_PER_TICK.
  - No internal retries; a claim failure logs and continues (the next
    tick re-evaluates state from the filesystem).
  - When ``HERMES3D_QUEUE_POLLER_DISABLED=1`` is set, the poller does
    not start. Operator can use HTTP endpoints to drive claims manually
    even with the poller off.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from hermes3d.services import queue_bridge

LOG = logging.getLogger(__name__)


# NOTE: These functions read env at CALL time (not import time) so tests
# and operators can re-tune the poller live without re-importing the
# module. Keep them cheap — they are called every tick.
def _poll_interval_secs() -> float:
    return float(os.environ.get("HERMES3D_QUEUE_POLL_INTERVAL", "15"))


def _max_claims_per_tick() -> int:
    return int(os.environ.get("HERMES3D_QUEUE_MAX_CLAIMS_PER_TICK", "3"))


# Kept as module-level constants for backward compatibility / import sites.
# Prefer the functions above for new callers.
POLL_INTERVAL_SECS = _poll_interval_secs()
MAX_CLAIMS_PER_TICK = _max_claims_per_tick()


def _workspace_root() -> Path:
    env_root = os.environ.get("HERMES3D_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[4]


def _available_personas() -> list[str]:
    """Resolve the live persona roster.

    Imports lazily to avoid circular imports during app construction. If
    the agent registry has not initialised yet (e.g. early startup), an
    empty list is returned and this tick is a no-op.
    """
    try:
        # PERSONAS is the static roster shared by /api/agents/health and
        # the agent registry. Imported lazily so test code can monkeypatch.
        from hermes3d.api.routes.agents import PERSONAS  # type: ignore

        return list(PERSONAS)
    except Exception as exc:
        LOG.debug("queue_poller: persona roster unavailable yet: %s", exc)
        return []


def _heartbeat_our_claims(root: Path, personas: set[str]) -> int:
    """Refresh heartbeat on every claimed task owned by one of our
    personas. Returns the number of heartbeats written."""
    refreshed = 0
    for snap in queue_bridge.list_tasks(root, "claimed"):
        owner = snap.claimed_by or ""
        if owner.startswith("hermes/"):
            persona = owner.split("/", 1)[1]
            if persona in personas:
                if queue_bridge.heartbeat(root, snap.task_id, persona=persona):
                    refreshed += 1
    return refreshed


def tick_once() -> dict[str, int]:
    """One poll cycle. Public so unit tests can drive it without
    spawning the asyncio loop."""
    root = _workspace_root()
    personas = _available_personas()
    if not personas:
        return {"personas": 0, "claimed": 0, "heartbeats": 0, "pending_seen": 0}
    persona_set = set(personas)

    # 1. Refresh heartbeats first so a long-running claimed task does not
    #    look stale to the orchestrator while we are also trying to claim.
    heartbeats = _heartbeat_our_claims(root, persona_set)

    # 2. Walk pending tasks in priority order (descending). The
    #    queue_bridge.list_tasks sort is by filename today; sort here
    #    explicitly so the contract does not depend on filesystem order.
    pending = queue_bridge.list_tasks(root, "pending")
    pending.sort(key=lambda t: (-t.priority, t.task_id))
    claimed_this_tick = 0
    seen = len(pending)
    max_per_tick = _max_claims_per_tick()
    for snap in pending:
        if claimed_this_tick >= max_per_tick:
            break
        matched = queue_bridge.match_persona(snap.target_owner_pattern, personas)
        if matched is None:
            continue
        result = queue_bridge.claim_task(root, snap.task_id, matched)
        if result is not None:
            LOG.info(
                "queue_poller: claimed task=%s persona=%s",
                snap.task_id,
                matched,
            )
            claimed_this_tick += 1
    return {
        "personas": len(personas),
        "claimed": claimed_this_tick,
        "heartbeats": heartbeats,
        "pending_seen": seen,
    }


async def run_forever() -> None:
    """Asyncio task body. Cancelled on shutdown by the FastAPI lifespan."""
    if os.environ.get("HERMES3D_QUEUE_POLLER_DISABLED") == "1":
        LOG.info("queue_poller: disabled by HERMES3D_QUEUE_POLLER_DISABLED=1")
        return
    interval = _poll_interval_secs()
    LOG.info(
        "queue_poller: starting; interval=%.1fs max_claims_per_tick=%d",
        interval,
        _max_claims_per_tick(),
    )
    while True:
        try:
            report = await asyncio.to_thread(tick_once)
            if report["claimed"] or report["heartbeats"]:
                LOG.info(
                    "queue_poller: tick personas=%d pending=%d claimed=%d hb=%d",
                    report["personas"],
                    report["pending_seen"],
                    report["claimed"],
                    report["heartbeats"],
                )
        except asyncio.CancelledError:
            LOG.info("queue_poller: cancelled — shutting down")
            raise
        except Exception as exc:  # pragma: no cover - defensive
            # Never let a single broken tick kill the poller.
            LOG.exception("queue_poller: tick failed: %s", exc)
        await asyncio.sleep(_poll_interval_secs())


__all__ = [
    "MAX_CLAIMS_PER_TICK",
    "POLL_INTERVAL_SECS",
    "run_forever",
    "tick_once",
]
