"""W6-7 (2026-05-09): runner for per-app ``proof_command``.

The proof_command on each module is a short, idempotent shell command
(typically ``--help`` / ``--version`` / ``python -c "import x"``). This
runner executes it under a strict timeout, captures stdout+stderr,
redacts secrets via ``hermes3d.gateways.redaction.redact_text``, and
returns an evidence-shaped dict that the API layer can persist.

Safety boundaries:
- Hard timeout (default 12 seconds, max 60).
- ``shell=True`` is intentional — proof commands are seeded by the
  Hermes operators, not user input. Untrusted input MUST NOT reach
  this function. The API route enforces the trust boundary.
- Output is truncated to 16 KiB after redaction.
- The function never raises on a non-zero exit code; the caller
  inspects ``exit_code`` and decides ``accepted`` per its policy.

Accepted proof status values (returned in ``status`` field):
- ``pass``      : exit_code == 0
- ``fail``      : exit_code != 0
- ``timeout``   : the command exceeded the timeout budget
- ``not_set``   : module has no proof_command on file
- ``error``     : the command failed to launch (FileNotFoundError, etc.)
"""

from __future__ import annotations

import shlex
import subprocess
import time
from typing import Any

from hermes3d.gateways.redaction import redact_text

DEFAULT_TIMEOUT_S = 12
MAX_TIMEOUT_S = 60
MAX_OUTPUT_BYTES = 16 * 1024


def run_proof_command(
    proof_command: str | None,
    *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Run ``proof_command`` and return a redacted evidence dict.

    Returns a dict with keys: ``status``, ``exit_code``, ``stdout``,
    ``stderr``, ``duration_ms``, ``command``, ``timed_out``,
    ``accepted``.

    ``accepted`` is a friendly boolean for the route layer: ``True`` if
    status == "pass". The API layer is free to apply additional policy
    (e.g. "warn but accept" for ``timeout``).
    """
    if not proof_command or not proof_command.strip():
        return {
            "status": "not_set",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "duration_ms": 0,
            "command": "",
            "timed_out": False,
            "accepted": False,
        }
    cmd = proof_command.strip()
    safe_timeout = max(1, min(int(timeout_s or DEFAULT_TIMEOUT_S), MAX_TIMEOUT_S))
    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S602 (intentional, see module docstring)
            cmd,
            shell=True,
            capture_output=True,
            timeout=safe_timeout,
            check=False,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        # Capture whatever was emitted before the kill.
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
        return {
            "status": "timeout",
            "exit_code": None,
            "stdout": redact_text(stdout),
            "stderr": redact_text(stderr),
            "duration_ms": elapsed_ms,
            "command": _redact_command(cmd),
            "timed_out": True,
            "accepted": False,
        }
    except (FileNotFoundError, OSError) as exc:
        # Command interpreter not available (rare on Linux/Win), or
        # cwd not found. Don't crash the API route.
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return {
            "status": "error",
            "exit_code": None,
            "stdout": "",
            "stderr": redact_text(str(exc))[:MAX_OUTPUT_BYTES],
            "duration_ms": elapsed_ms,
            "command": _redact_command(cmd),
            "timed_out": False,
            "accepted": False,
        }
    elapsed_ms = int((time.monotonic() - started) * 1000)
    stdout = completed.stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
    stderr = completed.stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
    status = "pass" if completed.returncode == 0 else "fail"
    return {
        "status": status,
        "exit_code": completed.returncode,
        "stdout": redact_text(stdout),
        "stderr": redact_text(stderr),
        "duration_ms": elapsed_ms,
        "command": _redact_command(cmd),
        "timed_out": False,
        "accepted": status == "pass",
    }


def _redact_command(cmd: str) -> str:
    """Echo the command back with secrets redacted.

    Useful when the command itself was seeded with a token (it
    shouldn't be, but defense-in-depth). We DO NOT shlex-split or
    canonicalize so the operator can see exactly what we ran.
    """
    return redact_text(cmd)


def parse_command(cmd: str) -> list[str]:
    """Best-effort tokenize for tests/inspection. NOT used to execute."""
    try:
        return shlex.split(cmd, posix=True)
    except ValueError:
        return [cmd]
