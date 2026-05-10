"""Single resolver for the Hermes Agent checkout path (12-Factor III).

Hermes Agent version coexistence (post Wave 1 promotion 2026-05-09):
- v0.13 production at ``G:/Github/hermes-agent-v013-canary``
  (v2026.5.7, "Tenacity Release"). This is the new default after Wave 1
  cleared 6/7 hard gates (live MiniMax + DeepSeek probes both
  ``accepted=true``; canary runtime smoke 8/8 imports + 10 MCP tools +
  redaction default-ON; production-untouched re-verify; per-call env
  resolver mid-process flip 4/4; zero secret leak). BLK-013 bounded
  task tracked separately.
- v0.12 fallback at ``G:/Github/hermes-agent-fresh`` (v2026.4.30). An
  operator can revert mid-process by setting
  ``HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`` (no restart;
  PR #155 made the resolver per-call).

Per-call read (Wave A5 / PR #155)
- ``DEFAULT_AGENT_CHECKOUT`` is no longer captured into a stale constant
  at module import. Each call to ``hermes_agent_checkout()`` reads
  ``os.environ.get`` live, so v0.13<->v0.12 swaps work mid-process.
"""

from __future__ import annotations

import os
from pathlib import Path

V012_FALLBACK_CHECKOUT = Path("G:/Github/hermes-agent-fresh")
"""v0.12 (v2026.4.30) fallback path. Operators set
``HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`` to revert."""

DEFAULT_AGENT_CHECKOUT = Path("G:/Github/hermes-agent-v013-canary")
"""Production default after Wave 1 promotion (2026-05-09). v0.13
(v2026.5.7) at the canary path. Used when ``HERMES_AGENT_CHECKOUT`` is
unset."""

CANARY_AGENT_CHECKOUT = DEFAULT_AGENT_CHECKOUT
"""Alias retained for tests / docs that referenced the canary path under
its pre-promotion name. Same path as ``DEFAULT_AGENT_CHECKOUT``."""


def hermes_agent_checkout() -> Path:
    """Return the active Hermes Agent checkout, honoring env per-call.

    Reads ``HERMES_AGENT_CHECKOUT`` from the live environment on every
    invocation so an operator can flip v0.13<->v0.12 without restarting
    the FastAPI process. Default = v0.13 production.
    """
    return Path(os.environ.get("HERMES_AGENT_CHECKOUT", str(DEFAULT_AGENT_CHECKOUT)))


__all__ = [
    "DEFAULT_AGENT_CHECKOUT",
    "CANARY_AGENT_CHECKOUT",
    "V012_FALLBACK_CHECKOUT",
    "hermes_agent_checkout",
]
