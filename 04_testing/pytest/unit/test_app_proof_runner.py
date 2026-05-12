from __future__ import annotations

import subprocess

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
