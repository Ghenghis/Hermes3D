"""Tests for the real-LLM MultiAgentLoop (Executor / Critic / Optimizer)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace


@dataclass
class _MockResult:
    text: str
    elapsed_seconds: float = 0.01
    raw: dict | None = None


class _MockProvider:
    def __init__(self, replies: list[str]):
        self._replies = list(replies)
        self.calls: list[tuple[str, str]] = []
        from hermes3d.core.llm.providers import LLMProvider

        self.config = SimpleNamespace(provider=LLMProvider.OLLAMA, model="mock")

    def available(self) -> bool:
        return True

    def generate(self, prompt: str, *, system: str | None = None) -> _MockResult:
        self.calls.append((system or "", prompt))
        text = self._replies.pop(0) if self._replies else "OK"
        return _MockResult(text=text, raw={"eval_count": len(text.split())})


def test_three_rounds_with_mock_provider():
    from hermes3d.core.agents.multi_agent import MultiAgentLoop

    provider = _MockProvider(["draft", "critique", "final"])
    loop = MultiAgentLoop(provider=provider)
    res = loop.run({"goal": "print bracket", "material": "PLA"})

    assert res.outcome == "ok"
    assert len(res.rounds) == 3
    roles = [r.role for r in res.rounds]
    assert roles == ["executor", "critic", "optimizer"]
    for r in res.rounds:
        assert r.prompt
        assert r.response
        assert r.latency_seconds >= 0
    assert res.final_draft == "final"
    assert provider.calls, "provider should have been invoked"


def test_provider_failure_returns_partial():
    from hermes3d.core.agents.multi_agent import MultiAgentLoop

    class _FailingProvider:
        config = SimpleNamespace(provider=None, model="x")

        def available(self):
            return True

        def generate(self, prompt, *, system=None):
            raise ConnectionError("backend down")

    loop = MultiAgentLoop(provider=_FailingProvider())
    res = loop.run({"goal": "diagnose"})
    assert res.outcome == "partial"
    assert res.rounds[0].error and "ConnectionError" in res.rounds[0].error


def test_no_provider_at_all_returns_no_llm(monkeypatch):
    """When auto-detect finds no provider, outcome is 'no-llm'."""
    from hermes3d.core.agents import multi_agent as ma

    def _fail_select(config=None):
        from hermes3d.core.llm.providers import ProviderUnavailable

        raise ProviderUnavailable("no backend")

    monkeypatch.setattr("hermes3d.core.llm.providers.select_provider", _fail_select)
    loop = ma.MultiAgentLoop()
    res = loop.run({"goal": "anything"})
    assert res.outcome == "no-llm"
    assert res.rounds == []
    assert res.message and "No LLM backend" in res.message


def test_result_is_json_serializable():
    from hermes3d.core.agents.multi_agent import MultiAgentLoop

    provider = _MockProvider(["a", "b", "c"])
    res = MultiAgentLoop(provider=provider).run({"goal": "x"})
    blob = json.dumps(res.to_dict())
    parsed = json.loads(blob)
    assert parsed["outcome"] == "ok"
    assert len(parsed["rounds"]) == 3
    assert parsed["final_draft"] == "c"
