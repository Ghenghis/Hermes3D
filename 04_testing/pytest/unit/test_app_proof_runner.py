from __future__ import annotations

import subprocess
from pathlib import Path

from hermes3d.services import app_proof_runner


def test_run_proof_timeout_kills_process_tree(monkeypatch):
    """Timed-out shell proof commands must reap their child process tree."""

    class FakeProcess:
        pid = 12345
        returncode = None

        def __init__(self) -> None:
            self.calls = 0
            self.killed = False

        def communicate(self, timeout=None):  # noqa: ANN001
            if self.calls == 0:
                self.calls += 1
                raise subprocess.TimeoutExpired(cmd="fake-proof", timeout=timeout)
            self.returncode = -9
            return b"partial stdout", b"partial stderr"

        def kill(self) -> None:
            self.killed = True

    fake = FakeProcess()
    killed: list[int] = []

    def fake_popen(*args, **kwargs):  # noqa: ANN002, ANN003
        return fake

    monkeypatch.setattr(app_proof_runner.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(app_proof_runner, "_kill_process_tree", lambda pid: killed.append(pid))

    result = app_proof_runner.run_proof_command("uvx blender-mcp --help", timeout_s=1)

    assert result["status"] == "timeout"
    assert result["timed_out"] is True
    assert result["accepted"] is False
    assert result["exit_code"] is None
    assert result["stdout"] == "partial stdout"
    assert "partial stderr" in result["stderr"]
    assert "process tree killed" in result["stderr"]
    assert killed == [12345]
    assert fake.killed is False


def test_seeded_command_resolves_known_windows_tool_when_not_on_path(monkeypatch, tmp_path):
    tool = tmp_path / "Tool App" / "tool.exe"
    tool.parent.mkdir()
    tool.write_text("fake")
    monkeypatch.setattr(app_proof_runner.shutil, "which", lambda token: None)
    monkeypatch.setitem(app_proof_runner.WINDOWS_TOOL_FALLBACKS, "tool", (str(tool),))

    resolved = app_proof_runner._resolve_seeded_command("tool --version")

    assert resolved == f'"{tool}" --version'


def test_seeded_command_leaves_path_tool_unchanged(monkeypatch, tmp_path):
    fallback = tmp_path / "fallback.exe"
    fallback.write_text("fake")
    monkeypatch.setattr(app_proof_runner.shutil, "which", lambda token: f"C:/bin/{token}.exe")
    monkeypatch.setitem(app_proof_runner.WINDOWS_TOOL_FALLBACKS, "blender", (str(fallback),))

    assert app_proof_runner._resolve_seeded_command("blender --version") == "blender --version"


def test_seeded_python_import_uses_sidecar_when_probe_passes(monkeypatch, tmp_path):
    sidecar = tmp_path / "proof python" / "python.exe"
    sidecar.parent.mkdir()
    sidecar.write_text("fake")
    probes: list[tuple[list[str], int]] = []

    def fake_run(args, **kwargs):  # noqa: ANN001, ANN003
        probes.append((args, kwargs["timeout"]))
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(app_proof_runner, "APP_PROOF_PYTHON_FALLBACKS", (str(sidecar),))
    monkeypatch.setattr(app_proof_runner.subprocess, "run", fake_run)
    app_proof_runner._PYTHON_IMPORT_RESOLUTION_CACHE.clear()

    resolved = app_proof_runner._resolve_seeded_command(
        'python -c "import cadquery;print(cadquery.__version__)"'
    )

    assert resolved == f'"{sidecar}" -c "import cadquery;print(cadquery.__version__)"'
    assert probes == [
        ([str(sidecar), "-c", "import cadquery"], app_proof_runner.PYTHON_IMPORT_PROBE_TIMEOUT_S)
    ]


def test_seeded_python_import_stays_original_when_sidecar_probe_fails(monkeypatch, tmp_path):
    sidecar = tmp_path / "python.exe"
    sidecar.write_text("fake")

    def fake_run(args, **kwargs):  # noqa: ANN001, ANN003
        return subprocess.CompletedProcess(args, 1, b"", b"missing")

    monkeypatch.setattr(app_proof_runner, "APP_PROOF_PYTHON_FALLBACKS", (str(sidecar),))
    monkeypatch.setattr(app_proof_runner.subprocess, "run", fake_run)
    app_proof_runner._PYTHON_IMPORT_RESOLUTION_CACHE.clear()

    command = 'python -c "import open3d;print(open3d.__version__)"'

    assert app_proof_runner._resolve_seeded_command(command) == command


def test_seeded_python_non_import_command_does_not_use_sidecar(monkeypatch, tmp_path):
    sidecar = tmp_path / "python.exe"
    sidecar.write_text("fake")

    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("sidecar probe should not run")

    monkeypatch.setattr(app_proof_runner, "APP_PROOF_PYTHON_FALLBACKS", (str(sidecar),))
    monkeypatch.setattr(app_proof_runner.subprocess, "run", fail_if_called)
    app_proof_runner._PYTHON_IMPORT_RESOLUTION_CACHE.clear()

    command = "python -c \"print('proof-ok')\""

    assert app_proof_runner._resolve_seeded_command(command) == command


def test_app_proof_python_candidates_prefers_env_and_deduplicates(monkeypatch, tmp_path):
    env_python = tmp_path / "env" / "python.exe"
    fallback_python = tmp_path / "fallback" / "python.exe"
    for path in (env_python, fallback_python):
        path.parent.mkdir()
        path.write_text("fake")
    monkeypatch.setenv("HERMES3D_APP_PROOF_PYTHON", str(env_python))
    monkeypatch.setattr(
        app_proof_runner,
        "APP_PROOF_PYTHON_FALLBACKS",
        (str(env_python), str(fallback_python), str(Path("Z:/missing/python.exe"))),
    )

    assert app_proof_runner._app_proof_python_candidates() == (
        str(env_python),
        str(fallback_python),
    )
