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

import os
import shlex
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from hermes3d.gateways.redaction import redact_text

DEFAULT_TIMEOUT_S = 12
MAX_TIMEOUT_S = 60
MAX_OUTPUT_BYTES = 16 * 1024

WINDOWS_TOOL_FALLBACKS: dict[str, tuple[str, ...]] = {
    "blender": (
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    ),
    "openscad": (
        r"C:\Program Files\OpenSCAD\openscad.exe",
        r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
        r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe",
    ),
    "curaengine": (
        r"C:\Program Files\UltiMaker Cura 5.12.1\CuraEngine.exe",
        r"C:\Program Files\Ultimaker Cura\CuraEngine.exe",
        r"C:\Program Files\Ultimaker Cura 4.13.1\CuraEngine.exe",
    ),
}

APP_PROOF_PYTHON_FALLBACKS: tuple[str, ...] = (
    r"G:\Gen3D\envs\hermes3d-app-proofs-py312\Scripts\python.exe",
    r"C:\Python312\python.exe",
)
APP_PROOF_SIDECAR_IMPORTS: tuple[str, ...] = (
    "build123d",
    "cadquery",
    "langchain",
    "open3d",
    "pymeshfix",
    "stl",
)
APP_PROOF_NODE_MODULE_FALLBACKS: tuple[str, ...] = (
    r"G:\Gen3D\envs\hermes3d-node-proofs\node_modules",
)
APP_PROOF_NODE_PACKAGES: tuple[str, ...] = ("microsoft-cognitiveservices-speech-sdk",)
PYTHON_IMPORT_PROBE_TIMEOUT_S = 30
_PYTHON_IMPORT_RESOLUTION_CACHE: dict[str, str | None] = {}
_NODE_PACKAGE_RESOLUTION_CACHE: dict[str, str | None] = {}


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
    cmd = _resolve_seeded_command(proof_command.strip())
    safe_timeout = max(1, min(int(timeout_s or DEFAULT_TIMEOUT_S), MAX_TIMEOUT_S))
    started = time.monotonic()
    try:
        proc = subprocess.Popen(  # noqa: S602 (intentional, see module docstring)
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            **_process_group_kwargs(),
        )
        try:
            stdout_raw, stderr_raw = proc.communicate(timeout=safe_timeout)
        except subprocess.TimeoutExpired:
            _kill_process_tree(proc.pid)
            try:
                stdout_raw, stderr_raw = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_raw, stderr_raw = proc.communicate()
            elapsed_ms = int((time.monotonic() - started) * 1000)
            stdout = _decode_output(stdout_raw)
            stderr = _decode_output(stderr_raw)
            timeout_note = "Proof command process tree killed after timeout."
            stderr = (stderr + ("\n" if stderr else "") + timeout_note)[:MAX_OUTPUT_BYTES]
            return {
                "status": "timeout",
                "exit_code": None,
                "stdout": redact_text(stdout[:MAX_OUTPUT_BYTES]),
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
    stdout = _decode_output(stdout_raw)[:MAX_OUTPUT_BYTES]
    stderr = _decode_output(stderr_raw)[:MAX_OUTPUT_BYTES]
    return_code = proc.returncode
    status = "pass" if return_code == 0 else "fail"
    return {
        "status": status,
        "exit_code": return_code,
        "stdout": redact_text(stdout),
        "stderr": redact_text(stderr),
        "duration_ms": elapsed_ms,
        "command": _redact_command(cmd),
        "timed_out": False,
        "accepted": status == "pass",
    }


def _process_group_kwargs() -> dict[str, Any]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _kill_process_tree(pid: int) -> None:
    """Terminate a timed-out shell and its children.

    ``subprocess.run(..., timeout=...)`` only kills the immediate shell on
    Windows. Tools like ``uvx`` can leave Python child processes running, which
    makes the app proof sweep hang and contaminates later probes. Use taskkill
    on Windows and a process group on POSIX.
    """

    if pid <= 0:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            return


def _decode_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def _redact_command(cmd: str) -> str:
    """Echo the command back with secrets redacted.

    Useful when the command itself was seeded with a token (it
    shouldn't be, but defense-in-depth). We DO NOT shlex-split or
    canonicalize so the operator can see exactly what we ran.
    """
    return redact_text(cmd)


def _resolve_seeded_command(cmd: str) -> str:
    """Resolve known seeded proof commands to real local tool paths.

    The 60-app registry is supposed to report whether local tools are usable,
    not whether the operator remembered to put every desktop app on PATH.
    Keep this intentionally tiny: only replace the first token for known,
    operator-seeded commands, and leave everything else unchanged.
    """

    python_resolved = _resolve_python_import_command(cmd)
    if python_resolved is not None:
        return python_resolved
    node_resolved = _resolve_node_require_command(cmd)
    if node_resolved is not None:
        return node_resolved

    token, suffix = _split_first_token(cmd)
    if not token:
        return cmd
    resolved = _resolve_tool_token(token)
    if resolved is None:
        return cmd
    return f"{_quote_shell_path(resolved)}{suffix}"


def _resolve_python_import_command(cmd: str) -> str | None:
    """Route selected Python import proofs through an import-capable sidecar.

    The backend currently runs on Python 3.14, while several CAD/modeling
    wheels are available only on older supported runtimes. This resolver is
    deliberately proof-specific: it rewrites only seeded ``python -c
    "import ..."`` commands for known app-proof modules, and only when the
    sidecar interpreter proves it can import that exact module.
    """

    module = _extract_sidecar_import_module(cmd)
    if module is None:
        return None
    python_path = _resolve_python_for_import(module)
    if python_path is None:
        return None
    _token, suffix = _split_first_token(cmd)
    return f"{_quote_shell_path(python_path)}{suffix}"


def _extract_sidecar_import_module(cmd: str) -> str | None:
    token, _suffix = _split_first_token(cmd)
    if not token:
        return None
    name = Path(token).name.lower()
    if name not in {"python", "python.exe", "py", "py.exe"}:
        return None
    try:
        tokens = shlex.split(cmd, posix=False)
    except ValueError:
        return None
    normalized = [token.strip("\"'") for token in tokens]
    if "-c" not in normalized:
        return None
    index = normalized.index("-c")
    if index + 1 >= len(normalized):
        return None
    script = normalized[index + 1]
    for module in APP_PROOF_SIDECAR_IMPORTS:
        if _script_imports_module(script, module):
            return module
    return None


def _script_imports_module(script: str, module: str) -> bool:
    normalized = script.replace("\n", " ").replace("\r", " ")
    return (
        f"import {module}" in normalized
        or f"from {module} " in normalized
        or f"from {module}." in normalized
    )


def _resolve_python_for_import(module: str) -> str | None:
    if module in _PYTHON_IMPORT_RESOLUTION_CACHE:
        return _PYTHON_IMPORT_RESOLUTION_CACHE[module]
    resolved: str | None = None
    for candidate in _app_proof_python_candidates():
        if _python_can_import(candidate, module):
            resolved = candidate
            break
    _PYTHON_IMPORT_RESOLUTION_CACHE[module] = resolved
    return resolved


def _app_proof_python_candidates() -> tuple[str, ...]:
    candidates: list[str] = []
    env_candidate = os.environ.get("HERMES3D_APP_PROOF_PYTHON")
    if env_candidate:
        candidates.append(env_candidate)
    candidates.extend(APP_PROOF_PYTHON_FALLBACKS)

    seen: set[str] = set()
    existing: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        key = str(Path(candidate)).lower()
        if key in seen:
            continue
        seen.add(key)
        if Path(candidate).exists():
            existing.append(candidate)
    return tuple(existing)


def _python_can_import(python_path: str, module: str) -> bool:
    try:
        result = subprocess.run(
            [python_path, "-c", f"import {module}"],
            capture_output=True,
            timeout=PYTHON_IMPORT_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _resolve_node_require_command(cmd: str) -> str | None:
    """Route selected Node ``require(...)`` proofs to a package sidecar.

    Source checkouts are not always built Node packages. The Azure Speech SDK
    JS checkout, for example, has TypeScript source but no ``distrib`` output.
    Only rewrite known seeded package proofs after a sidecar package can be
    required successfully.
    """

    package = _extract_sidecar_node_package(cmd)
    if package is None:
        return None
    package_path = _resolve_node_package(package)
    if package_path is None:
        return None
    return _replace_node_package_require(cmd, package, package_path)


def _extract_sidecar_node_package(cmd: str) -> str | None:
    token, _suffix = _split_first_token(cmd)
    if not token:
        return None
    name = Path(token).name.lower()
    if name not in {"node", "node.exe"}:
        return None
    try:
        tokens = shlex.split(cmd, posix=False)
    except ValueError:
        return None
    normalized = [token.strip("\"'") for token in tokens]
    if "-e" not in normalized:
        return None
    index = normalized.index("-e")
    if index + 1 >= len(normalized):
        return None
    script = normalized[index + 1]
    for package in APP_PROOF_NODE_PACKAGES:
        if f"require('{package}')" in script or f'require("{package}")' in script:
            return package
    return None


def _resolve_node_package(package: str) -> str | None:
    if package in _NODE_PACKAGE_RESOLUTION_CACHE:
        return _NODE_PACKAGE_RESOLUTION_CACHE[package]
    resolved: str | None = None
    for node_modules in _app_proof_node_module_candidates():
        candidate = Path(node_modules) / package
        if candidate.exists() and _node_can_require(candidate):
            resolved = candidate.as_posix()
            break
    _NODE_PACKAGE_RESOLUTION_CACHE[package] = resolved
    return resolved


def _app_proof_node_module_candidates() -> tuple[str, ...]:
    candidates: list[str] = []
    env_candidate = os.environ.get("HERMES3D_APP_PROOF_NODE_MODULES")
    if env_candidate:
        candidates.append(env_candidate)
    candidates.extend(APP_PROOF_NODE_MODULE_FALLBACKS)

    seen: set[str] = set()
    existing: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        key = str(Path(candidate)).lower()
        if key in seen:
            continue
        seen.add(key)
        if Path(candidate).exists():
            existing.append(candidate)
    return tuple(existing)


def _node_can_require(package_path: Path) -> bool:
    try:
        result = subprocess.run(
            ["node", "-e", f"require('{package_path.as_posix()}')"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _replace_node_package_require(cmd: str, package: str, package_path: str) -> str:
    return cmd.replace(f"require('{package}')", f"require('{package_path}')").replace(
        f'require("{package}")', f"require('{package_path}')"
    )


def _split_first_token(cmd: str) -> tuple[str, str]:
    stripped = cmd.lstrip()
    leading = cmd[: len(cmd) - len(stripped)]
    if not stripped:
        return "", ""
    try:
        tokens = shlex.split(stripped, posix=False)
    except ValueError:
        tokens = []
    if not tokens:
        parts = stripped.split(maxsplit=1)
        token = parts[0]
    else:
        token = tokens[0].strip("\"'")
    suffix_start = len(leading) + len(token)
    # Handle quoted first tokens by advancing over the closing quote.
    if stripped[0] in "\"'":
        quote = stripped[0]
        end = cmd.find(quote, len(leading) + 1)
        if end != -1:
            suffix_start = end + 1
    return token, cmd[suffix_start:]


def _resolve_tool_token(token: str) -> str | None:
    name = Path(token).name.lower()
    if name.endswith(".exe"):
        name = name[:-4]
    if shutil.which(token):
        return None
    for candidate in WINDOWS_TOOL_FALLBACKS.get(name, ()):
        if Path(candidate).exists():
            return candidate
    return None


def _quote_shell_path(path: str) -> str:
    escaped = path.replace('"', '\\"')
    return f'"{escaped}"'


def parse_command(cmd: str) -> list[str]:
    """Best-effort tokenize for tests/inspection. NOT used to execute."""
    try:
        return shlex.split(cmd, posix=True)
    except ValueError:
        return [cmd]
