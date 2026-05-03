from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "scaffolding" / "doctor.sh"


def _bash() -> str:
    candidates = [
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files/Git/usr/bin/bash.exe"),
    ]
    found = shutil.which("bash")
    if found and "Windows\\system32" not in found:
        return found
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    if found and "Windows\\system32" not in found:
        return found
    pytest.skip("Git Bash or POSIX bash is not available on this runner")


def _bash_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if drive:
        tail = resolved.as_posix()[2:]
        return f"/{drive}{tail}"
    return resolved.as_posix()


def _run_doctor(platform: str, **overrides: str) -> dict[str, object]:
    env = os.environ.copy()
    env.update(
        {
            "HERMES3D_DOCTOR_PLATFORM": platform,
            "HERMES3D_DOCTOR_PYTHON_VERSION": "3.14.3",
            "HERMES3D_DOCTOR_PORT_8080_FREE": "true",
            "HERMES3D_DOCTOR_GIT_PRESENT": "true",
        }
    )
    env.update(overrides)
    completed = subprocess.run(
        [_bash(), _bash_path(SCRIPT), "--json"],
        check=True,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(completed.stdout)


def _by_id(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    checks = payload["checks"]
    assert isinstance(checks, list)
    return {str(c["id"]): c for c in checks if isinstance(c, dict)}


def test_doctor_sh_json_linux_reports_libgl_and_skips_windows_checks() -> None:
    payload = _run_doctor("linux", HERMES3D_DOCTOR_LIBGL_PRESENT="true")
    checks = _by_id(payload)

    assert payload["json_schema_version"] == 1
    assert payload["platform"] == "linux"
    assert payload["ok"] is True
    assert checks["wsl2_present"]["ok"] is None
    assert checks["kernel_version"]["ok"] is None
    assert checks["python_3_11_or_12"]["ok"] is True
    assert checks["port_8080_free"]["ok"] is True
    assert checks["libgl_present"]["ok"] is True
    assert checks["git_present"]["ok"] is True


def test_doctor_sh_json_macos_skips_linux_and_windows_checks() -> None:
    payload = _run_doctor("macos")
    checks = _by_id(payload)

    assert payload["platform"] == "macos"
    assert payload["ok"] is True
    assert checks["wsl2_present"]["ok"] is None
    assert checks["kernel_version"]["ok"] is None
    assert checks["libgl_present"]["ok"] is None
