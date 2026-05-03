from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "scaffolding" / "doctor.ps1"


def _pwsh() -> str:
    for candidate in ("pwsh", "powershell"):
        found = shutil.which(candidate)
        if found is not None:
            return found
    pytest.skip("PowerShell is not available on this runner")


def _run_doctor(**overrides: str) -> dict[str, object]:
    env = os.environ.copy()
    env.update(
        {
            "HERMES3D_DOCTOR_PLATFORM": "windows",
            "HERMES3D_DOCTOR_PYTHON_VERSION": "3.14.3",
            "HERMES3D_DOCTOR_PORT_8080_FREE": "true",
            "HERMES3D_DOCTOR_GIT_PRESENT": "true",
        }
    )
    env.update(overrides)
    completed = subprocess.run(
        [_pwsh(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "--json"],
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


def test_doctor_ps1_json_windows_wsl_present() -> None:
    payload = _run_doctor(
        HERMES3D_DOCTOR_WSL_PRESENT="true",
        HERMES3D_DOCTOR_KERNEL_VERSION="5.15.90",
    )
    checks = _by_id(payload)

    assert payload["json_schema_version"] == 1
    assert payload["platform"] == "windows"
    assert payload["ok"] is True
    assert checks["wsl2_present"]["ok"] is True
    assert checks["kernel_version"]["ok"] is True
    assert checks["python_3_11_or_12"]["ok"] is True
    assert checks["port_8080_free"]["ok"] is True
    assert checks["libgl_present"]["ok"] is None
    assert checks["git_present"]["ok"] is True


def test_doctor_ps1_json_windows_wsl_absent_fails_with_hint() -> None:
    payload = _run_doctor(
        HERMES3D_DOCTOR_WSL_PRESENT="false",
        HERMES3D_DOCTOR_KERNEL_VERSION="5.15.90",
    )
    checks = _by_id(payload)

    assert payload["ok"] is False
    assert checks["wsl2_present"]["ok"] is False
    assert "Install WSL2" in " ".join(payload["fix_hints"])


def test_doctor_ps1_json_windows_old_kernel_fails_with_hint() -> None:
    payload = _run_doctor(
        HERMES3D_DOCTOR_WSL_PRESENT="true",
        HERMES3D_DOCTOR_KERNEL_VERSION="4.19.128",
    )
    checks = _by_id(payload)

    assert payload["ok"] is False
    assert checks["kernel_version"]["ok"] is False
    assert "Update WSL kernel" in " ".join(payload["fix_hints"])
