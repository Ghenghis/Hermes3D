"""Single resolver for the Hermes Agent checkout path (12-Factor III).

Hermes Agent v0.13 Canary Switch (PR follow-up):
- Production checkout lives at ``G:/Github/hermes-agent-fresh`` (v0.12).
- Canary checkout lives at ``G:/Github/hermes-agent-v013-canary`` (v0.13).
- An operator selects between them by setting ``HERMES_AGENT_CHECKOUT`` in
  the environment for the FastAPI process.

Pre-resolver state (Hermes-Agent-Only Wave A finding A5):
- ``api/routes/agent_updates.py:25`` reads ``HERMES_AGENT_CHECKOUT`` at
  module-import time and stores the result in ``DEFAULT_CHECKOUT``. Any
  env flip after import is silently ignored — process restart required.
- Three sister modules ignore the env entirely and pin
  ``G:/Github/hermes-agent-fresh`` as a string literal.

This resolver fixes both issues by reading the env per-call and exposing
a single resolution function the four module sites can share.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_AGENT_CHECKOUT = Path("G:/Github/hermes-agent-fresh")
"""Production v0.12 path. Used when ``HERMES_AGENT_CHECKOUT`` is unset."""

CANARY_AGENT_CHECKOUT = Path("G:/Github/hermes-agent-v013-canary")
"""Canary v0.13 path. Set ``HERMES_AGENT_CHECKOUT=...`` to point here."""


def hermes_agent_checkout() -> Path:
    """Return the active Hermes Agent checkout, honoring env per-call.

    Reads ``HERMES_AGENT_CHECKOUT`` from the live environment on every
    invocation so an operator can flip canary↔production without
    restarting the FastAPI process. Default = production v0.12.
    """
    return Path(os.environ.get("HERMES_AGENT_CHECKOUT", str(DEFAULT_AGENT_CHECKOUT)))


__all__ = ["DEFAULT_AGENT_CHECKOUT", "CANARY_AGENT_CHECKOUT", "hermes_agent_checkout"]
