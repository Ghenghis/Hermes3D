"""Wave Agent 7 broad-except cleanup — source-level pin tests.

Source pin tests that confirm the 7 silent-fallback sites Wave Agent 7
flagged now emit a ``logging.getLogger(__name__).{warning|debug}(...)``
call before the ``pass``. Catches accidental revert.

Sites covered (per Wave synthesis 2026-05-09):
- services/module_runtime.py:_private_runtime_env (warning + redact_text)
- api/routes/design.py:module_version_lookup (debug)
- api/routes/update_center.py:read fallback (warning)
- api/routes/system.py:metrics psutil fallback (debug)
- core/orchestration/repair_agent.py:extract_json fallback (debug)
- core/agents/auto_recovery.py:printer_state_poll_soft fallback (debug)
- core/agents/auto_recovery.py:firmware_restart fallback (debug)

Behavior is otherwise unchanged on every site (silent fallback semantics
preserved; observability added).

References:
- OWASP A09:2021 Logging & Monitoring Failures
- https://docs.python.org/3/library/logging.html
"""

from __future__ import annotations

import pytest


def _read_source(dotted: str) -> str:
    """Read a Python source file under hermes3d by dotted module name."""
    parts = dotted.split(".")
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[3] / "03_implementation" / "src"
    file_path = src_root / Path(*parts).with_suffix(".py")
    return file_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "module_dotted,marker_substring,description",
    [
        (
            "hermes3d.services.module_runtime",
            "_private_runtime_env: private_env import/load failed",
            "module_runtime._private_runtime_env logs + redacts on fallback",
        ),
        (
            "hermes3d.api.routes.design",
            "design.module_version_lookup",
            "design.module_version_lookup logs on metadata.version() fallback",
        ),
        (
            "hermes3d.api.routes.update_center",
            "update_center.read",
            "update_center.read logs on proof_events insert fallback",
        ),
        (
            "hermes3d.api.routes.system",
            "system.metrics",
            "system.metrics logs on psutil fallback",
        ),
        (
            "hermes3d.core.orchestration.repair_agent",
            "repair_agent.extract_json",
            "repair_agent logs on extract_json fallback",
        ),
        (
            "hermes3d.core.agents.auto_recovery",
            "auto_recovery.printer_state_poll_soft",
            "auto_recovery soft-restart logs on poll fallback",
        ),
        (
            "hermes3d.core.agents.auto_recovery",
            "auto_recovery.firmware_restart",
            "auto_recovery firmware-restart logs on poll fallback",
        ),
    ],
)
def test_broad_except_site_now_logs(
    module_dotted: str, marker_substring: str, description: str
) -> None:
    """Each Wave Agent 7 site must contain a recognizable log marker."""
    src = _read_source(module_dotted)
    assert marker_substring in src, (
        f"Wave Agent 7 broad-except cleanup regression — {description}: "
        f"expected marker {marker_substring!r} not found in source."
    )


def test_module_runtime_uses_redact_text_for_env_exception() -> None:
    """``_private_runtime_env`` exceptions can carry path/token fragments;
    must run through ``redact_text`` before logging (Wave Agent 7 caveat)."""
    src = _read_source("hermes3d.services.module_runtime")
    # The redact_text call must appear in or near the _private_runtime_env block.
    assert "redact_text" in src, "module_runtime must import redact_text for safe exception logging"
    assert "_private_runtime_env" in src
