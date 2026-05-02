"""Provider probe CLI tests."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from hermes3d.cli import probe as probe_cli
from hermes3d.gateways.probe import ProbeOutcome
from hermes3d.gateways.providers import ProbePolicy
from hermes3d.orchestration.ledger import OrchestrationLedger
from hermes3d.orchestration.types import ProviderConfig


class _FakeAdapter:
    def __init__(self, *, http_status: int, body: str) -> None:
        self.http_status = http_status
        self.body = body

    def probe_caller(self, _config: ProviderConfig):
        def _caller(_cfg: ProviderConfig) -> ProbeOutcome:
            return ProbeOutcome(http_status=self.http_status, latency_ms=7, body=self.body)

        return _caller


def _config() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://api.minimax.io/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="HERMES3D_MINIMAX_API_KEY",
        cost_cap_usd_per_run=Decimal("0.05"),
        cost_cap_usd_per_day=Decimal("1.00"),
    )


def _policy(*, providers: dict[str, ProviderConfig] | None = None) -> ProbePolicy:
    return ProbePolicy(
        providers={"minimax": _config()} if providers is None else providers,
        probe_freshness_minutes=15,
        probe_budget_usd_per_day=Decimal("0.10"),
        probe_rate_per_minute=1,
    )


def test_main_happy_path_returns_0_and_prints_redacted_json(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(probe_cli, "load_probe_policy", lambda: _policy())
    ledger_path = tmp_path / "events.sqlite3"

    code = probe_cli.main(
        ["minimax", "--ledger-path", str(ledger_path)],
        adapters={"minimax": _FakeAdapter(http_status=200, body='{"data":[{"id":"m"}]}')},
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["success"] is True
    assert payload["http_status"] == 200
    event = OrchestrationLedger(ledger_path).events()[0]
    assert event.tool == "provider.probe"
    assert event.verdict == "pass"


def test_main_failed_probe_returns_1(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(probe_cli, "load_probe_policy", lambda: _policy())
    ledger_path = tmp_path / "events.sqlite3"

    code = probe_cli.main(
        ["minimax", "--ledger-path", str(ledger_path)],
        adapters={"minimax": _FakeAdapter(http_status=500, body='{"error":"down"}')},
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["success"] is False
    event = OrchestrationLedger(ledger_path).events()[0]
    assert event.verdict == "fail"


def test_main_unknown_provider_argparse_error() -> None:
    with pytest.raises(SystemExit) as exc:
        probe_cli.main(["unknown_provider"])

    assert exc.value.code == 2


def test_main_provider_in_argparse_but_not_in_policy_returns_2(
    tmp_path, capsys, monkeypatch
) -> None:
    monkeypatch.setattr(probe_cli, "load_probe_policy", lambda: _policy(providers={}))

    code = probe_cli.main(["minimax", "--ledger-path", str(tmp_path / "events.sqlite3")])

    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["code"] == "provider_not_in_policy"
