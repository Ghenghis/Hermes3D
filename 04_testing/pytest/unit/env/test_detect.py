"""Phase 1 Task 18 — env-detect cascade tests (mocked subprocess only)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import jsonschema
from hermes3d.env import detect as detect_mod
from hermes3d.env.detect import _try_nvidia_smi, _try_wmi, detect_env
from hermes3d.env.types import EnvReport

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).parent / "fixtures"
SCHEMA = REPO_ROOT / "schemas" / "env_report.schema.json"


class _FakeProc:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


def _runner_returning(stdout: str, rc: int = 0):
    """Build a runner stub that returns a fixed CompletedProcess-like object."""

    def _run(args, timeout=5.0):
        return _FakeProc(stdout=stdout, returncode=rc)

    return _run


def _runner_raising(exc: BaseException):
    def _run(args, timeout=5.0):
        raise exc

    return _run


# --------------------------- _try_nvidia_smi ---------------------------
def test_nvidia_smi_3090ti_parses():
    out = (FIXTURES / "nvidia_smi_3090ti.txt").read_text(encoding="utf-8")
    with patch("hermes3d.env.detect.shutil.which", return_value="/usr/bin/nvidia-smi"):
        ok, data = _try_nvidia_smi(_runner_returning(out))
    assert ok
    assert data["gpu_name"] == "NVIDIA GeForce RTX 3090 Ti"
    assert data["vram_total_mib"] == 24564
    assert data["vram_free_mib"] == 18493
    assert data["driver_version"] == "591.86"
    assert data["cuda_available"] is True
    assert data["detection_source"] == "nvidia-smi"


def test_nvidia_smi_absent_returns_unavailable():
    with patch("hermes3d.env.detect.shutil.which", return_value=None):
        ok, data = _try_nvidia_smi(_runner_returning(""))
    assert not ok
    assert data == {}


def test_nvidia_smi_empty_output_returns_unavailable():
    out = (FIXTURES / "nvidia_smi_no_gpu.txt").read_text(encoding="utf-8")
    with patch("hermes3d.env.detect.shutil.which", return_value="/usr/bin/nvidia-smi"):
        ok, data = _try_nvidia_smi(_runner_returning(out))
    assert not ok
    assert data == {}


def test_nvidia_smi_timeout_returns_unavailable():
    with patch("hermes3d.env.detect.shutil.which", return_value="/usr/bin/nvidia-smi"):
        ok, data = _try_nvidia_smi(_runner_raising(subprocess.TimeoutExpired("nvidia-smi", 5.0)))
    assert not ok
    assert data == {}


def test_nvidia_smi_oserror_returns_unavailable():
    with patch("hermes3d.env.detect.shutil.which", return_value="/usr/bin/nvidia-smi"):
        ok, data = _try_nvidia_smi(_runner_raising(OSError("denied")))
    assert not ok
    assert data == {}


# --------------------------- _try_wmi ---------------------------
def test_wmi_intel_only(monkeypatch):
    monkeypatch.setattr(detect_mod, "_platform_name", lambda: "windows")
    out = (FIXTURES / "wmi_intel_only.txt").read_text(encoding="utf-8")
    ok, data = _try_wmi(_runner_returning(out))
    assert ok
    assert data["vendor"] == "Intel"
    assert "Intel" in data["gpu_name"]
    assert data["detection_source"] == "wmi"
    assert data["cuda_available"] is False


def test_wmi_amd(monkeypatch):
    monkeypatch.setattr(detect_mod, "_platform_name", lambda: "windows")
    out = (FIXTURES / "wmi_amd.txt").read_text(encoding="utf-8")
    ok, data = _try_wmi(_runner_returning(out))
    assert ok
    assert data["vendor"] == "AMD"


def test_wmi_skipped_on_non_windows(monkeypatch):
    monkeypatch.setattr(detect_mod, "_platform_name", lambda: "linux")
    ok, data = _try_wmi(_runner_returning("Name\nNVIDIA GeForce"))
    assert not ok
    assert data == {}


# --------------------------- detect_env (full cascade) ---------------------------
def test_detect_env_returns_envreport_with_required_fields():
    """detect_env() must always return a fully-populated EnvReport, even
    when every cascade step fails."""

    def runner_always_fail(args, timeout=5.0):
        return _FakeProc(stdout="", returncode=1)

    with patch("hermes3d.env.detect.shutil.which", return_value=None):
        report = detect_env(runner=runner_always_fail)
    assert isinstance(report, EnvReport)
    assert report.platform in {"windows", "linux", "macos", "other"}
    assert report.edition in {"desktop_gpu_worker", "ubuntu_vps_control_server", "blocked_no_gpu"}
    assert report.detection_source == "unavailable"
    assert report.vendor == "none"
    assert report.cuda_available is False


def test_detect_env_picks_nvidia_smi_when_available(monkeypatch):
    """nvidia-smi is first in the cascade; when it succeeds, later steps don't run."""
    monkeypatch.setattr(detect_mod, "_platform_name", lambda: "linux")
    out = (FIXTURES / "nvidia_smi_3090ti.txt").read_text(encoding="utf-8")
    # Pretend nvidia-smi exists; node doesn't.
    which_results = {"nvidia-smi": "/usr/bin/nvidia-smi", "node": None}
    with (
        patch("hermes3d.env.detect.shutil.which", side_effect=lambda b: which_results.get(b, None)),
    ):
        report = detect_env(runner=_runner_returning(out))
    assert report.detection_source == "nvidia-smi"
    assert report.vendor == "NVIDIA"
    assert report.gpu_name == "NVIDIA GeForce RTX 3090 Ti"
    assert report.vram_total_mib == 24564
    assert report.cuda_available is True
    assert report.edition == "desktop_gpu_worker"  # linux + cuda


# --------------------------- JSON Schema conformance ---------------------------
def test_envreport_validates_against_jsonschema():
    """Live output of detect_env must conform to schemas/env_report.schema.json."""

    def runner_always_fail(args, timeout=5.0):
        return _FakeProc(stdout="", returncode=1)

    with patch("hermes3d.env.detect.shutil.which", return_value=None):
        report_dict = detect_env(runner=runner_always_fail).to_dict()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(report_dict, schema)


def test_envreport_with_full_nvidia_data_validates_jsonschema():
    """Populated report (including vram + driver) also passes schema."""
    out = (FIXTURES / "nvidia_smi_3090ti.txt").read_text(encoding="utf-8")
    which_results = {"nvidia-smi": "/usr/bin/nvidia-smi", "node": "/usr/bin/node"}

    def runner(args, timeout=5.0):
        if args[0] == "node":
            return _FakeProc(stdout="v25.8.2\n", returncode=0)
        return _FakeProc(stdout=out, returncode=0)

    with patch(
        "hermes3d.env.detect.shutil.which", side_effect=lambda b: which_results.get(b, None)
    ):
        report_dict = detect_env(runner=runner).to_dict()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(report_dict, schema)
    assert report_dict["node_version"] == "v25.8.2"
    assert report_dict["vendor"] == "NVIDIA"
