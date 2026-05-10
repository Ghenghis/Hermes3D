"""Bonus 12 finding #8 (Audit PR #135) — partial mitigation tests.

The audit recommended replacing the manual ``Popen + reader-thread + sleep
+ terminate/kill`` ladder in ``_call_mcp_tool`` with ``subprocess.run``.
That switch was tried and reverted: ``subprocess.run`` writes ``input``
then closes the child's stdin immediately, and the hermes3d MCP server
treats stdin EOF as a client disconnect — six ``test_recovery_*`` tests
caught the regression (``rc=0``,
``[hermesproof] shutdown: stdin EOF (client disconnect)``).

Partial mitigation kept in this PR:
- Reader threads are now explicitly ``join(timeout=1)``-ed in the finally
  block, so they no longer outlive the function call (the daemon=True
  thread leak Agent 9 of the swarm flagged).
- Env-pinning whitelist is preserved verbatim (security regression guard).

Full fix is **escalated** to BLK-009 in
``03_implementation/docs/handoffs/E2E_BLOCKER_REGISTRY_2026-05-09.md``;
proper resolution is either (a) server-side change to drain queued
messages on stdin EOF before shutdown, or (b) client switch to MCP HTTP
transport when it lands.

Tests in this file pin the partial mitigation in place so a future PR
that breaks env-pinning or re-leaks threads is caught.

References:
- https://docs.python.org/3/library/subprocess.html#subprocess.Popen.wait
- BLK-009 in E2E Blocker Registry
"""

from __future__ import annotations

import inspect

from hermes3d.services import code_history


def test_call_mcp_tool_joins_reader_threads() -> None:
    """The function source must contain explicit thread.join() calls so the
    daemon reader threads do not outlive the function (Bonus 12 #8 partial)."""
    src = inspect.getsource(code_history._call_mcp_tool)
    assert "stdout_thread.join" in src, (
        "Bonus 12 #8 regression: stdout reader thread must be explicitly "
        "joined in finally; otherwise daemon=True hides the leak."
    )
    assert "stderr_thread.join" in src, (
        "Bonus 12 #8 regression: stderr reader thread must be explicitly "
        "joined in finally; otherwise daemon=True hides the leak."
    )


def test_call_mcp_tool_env_pinning_whitelist_unchanged() -> None:
    """The env passed to the child must be a fixed whitelist plus the two
    MCP_LOCK_ overrides. Any drift is a security regression."""
    src = inspect.getsource(code_history._call_mcp_tool)
    # Whitelist keys (security-relevant)
    for required in ('"PATH"', '"PATHEXT"', '"SystemRoot"', '"COMSPEC"', '"TEMP"', '"TMP"'):
        assert required in src, f"Bonus 12 #8 regression: env whitelist missing {required}"
    # Overrides (must be set last)
    assert '"MCP_LOCK_WORKSPACE"' in src
    assert '"MCP_LOCK_SERVER"' in src
    # No widening: explicit "secret"-shaped names must NOT be in the source.
    for forbidden in (
        '"AWS_SECRET_ACCESS_KEY"',
        '"DEEPSEEK_API_KEY"',
        '"MINIMAX_API_KEY"',
        '"OPENAI_API_KEY"',
        '"NOUS_API_KEY"',
        '"GITHUB_TOKEN"',
    ):
        assert forbidden not in src, (
            f"Bonus 12 #8 regression: env-pinning whitelist widened to {forbidden}"
        )


def test_call_mcp_tool_workspace_check_present() -> None:
    """The workspace-mismatch guard must remain — defends against a poisoned
    MCP_LOCK_WORKSPACE pointing at a different repo."""
    src = inspect.getsource(code_history._call_mcp_tool)
    assert "MCP_LOCK_WORKSPACE" in src
    assert "PROJECT_ROOT" in src
    assert "MCP lock workspace" in src or "workspace does not match" in src


def test_call_mcp_tool_terminate_kill_ladder_preserved() -> None:
    """Until the upstream fix lands (BLK-009), keep the terminate->kill
    ladder so a hung child is reaped within ~3s of timeout."""
    src = inspect.getsource(code_history._call_mcp_tool)
    assert "process.terminate()" in src
    assert "process.kill()" in src
    assert "TimeoutExpired" in src


def test_blocker_009_documented_in_registry() -> None:
    """The full Bonus 12 #8 fix is escalated to BLK-009. Pin that the
    registry file references it so a future fix-PR is unambiguous."""
    from pathlib import Path

    registry = (
        Path(__file__).resolve().parents[3]
        / "03_implementation"
        / "docs"
        / "handoffs"
        / "E2E_BLOCKER_REGISTRY_2026-05-09.md"
    )
    assert registry.exists(), "E2E Blocker Registry must exist"
    text = registry.read_text(encoding="utf-8")
    assert "BLK-009" in text
    assert "_call_mcp_tool" in text or "MCP" in text
