"""Operator-triggered provider probe CLI."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from hermes3d.gateways.budget import fresh_budget_state
from hermes3d.gateways.probe import PROBE_TOOL, ProviderProbeGateway
from hermes3d.gateways.providers import deepseek, load_probe_policy, minimax
from hermes3d.orchestration.ledger import OrchestrationLedger
from hermes3d.orchestration.supervisor import OfflineSupervisor
from hermes3d.orchestration.types import Err, Ok

ADAPTERS = {"minimax": minimax, "deepseek": deepseek}
DEFAULT_LEDGER_PATH = Path("var/orchestration/provider_probe.sqlite3")


def main(argv: list[str] | None = None, *, adapters: dict[str, Any] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one bounded Hermes3D provider probe.")
    parser.add_argument("provider_id", choices=["minimax", "deepseek"])
    parser.add_argument("--ledger-path", default=str(DEFAULT_LEDGER_PATH))
    args = parser.parse_args(argv)

    active_adapters = adapters or ADAPTERS
    probe_policy = load_probe_policy()
    config = probe_policy.providers.get(args.provider_id)
    if config is None:
        _print_json(
            {"ok": False, "code": "provider_not_in_policy", "provider_id": args.provider_id}
        )
        return 2

    ledger = OrchestrationLedger(args.ledger_path)
    supervisor = OfflineSupervisor(ledger=ledger)
    budget = fresh_budget_state()
    token = supervisor.issue_token(
        agent_id="operator-cli",
        tools=frozenset({PROBE_TOOL}),
        scopes=frozenset({f"probe:{args.provider_id}"}),
        budget=budget,
    )
    if isinstance(token, Err):
        _print_json({"ok": False, "code": token.code, "message": token.message})
        return 3

    adapter = active_adapters[args.provider_id]
    gateway = ProviderProbeGateway(
        ledger=ledger,
        providers=probe_policy.providers,
        probe_freshness_minutes=probe_policy.probe_freshness_minutes,
        probe_budget_usd_per_day=probe_policy.probe_budget_usd_per_day,
        probe_rate_per_minute=probe_policy.probe_rate_per_minute,
        probe_caller=adapter.probe_caller(config),
    )
    result = gateway.probe(args.provider_id, token=token, budget=budget)
    if isinstance(result, Err):
        _print_json({"ok": False, "code": result.code, "message": result.message})
        return 4

    payload = _result_payload(result)
    _print_json(payload)
    return 0 if result.value.success else 1


def _result_payload(result: Ok) -> dict[str, object]:
    payload = asdict(result.value)
    payload["ok"] = True
    payload["message"] = result.message
    return payload


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, default=_json_default))


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
