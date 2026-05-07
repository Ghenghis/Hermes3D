"""Tests for the read-only print-farm verifier (H3D-CLAUDE-SOURCE-PRINTFARM).

These assert the proof JSON shape and lane policy invariants. They do NOT
require network access — they re-use the proof file produced by
`scripts/verify_printfarm.py`. If the proof file is absent, the test
regenerates it (which on a closed network will record honest unreachable
results, which is the correct outcome).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
IMPL_ROOT = REPO_ROOT / "03_implementation"
SCRIPT = IMPL_ROOT / "scripts" / "verify_printfarm.py"
PROOF = IMPL_ROOT / "proof" / "PRINTFARM_VERIFY_2026-05-06.json"

REQUIRED_TOP_KEYS = {
    "schema",
    "lane",
    "generated_at",
    "tool",
    "policy",
    "printers",
    "services",
    "summary",
}

REQUIRED_PRINTER_KEYS = {
    "name",
    "ip",
    "port",
    "service",
    "policy",
    "skipped",
    "reachable",
    "version",
    "url",
    "method",
    "error",
    "elapsed_ms",
}

REQUIRED_SERVICE_KEYS = {
    "service",
    "policy",
    "reachable",
    "version",
    "url",
    "method",
    "error",
    "elapsed_ms",
}

EXPECTED_PRINTER_NAMES = {"flsun_s1_camera", "flsun_t1_a", "flsun_t1_b", "flsun_v400"}
EXPECTED_SERVICES = {"fluidd", "mainsail", "octoprint", "fdm_monster", "klipperscreen", "printrun"}


@pytest.fixture(scope="module")
def proof() -> dict:
    if not PROOF.exists():
        subprocess.run([sys.executable, str(SCRIPT)], check=True, cwd=str(REPO_ROOT))
    assert PROOF.exists(), f"proof file not produced at {PROOF}"
    return json.loads(PROOF.read_text(encoding="utf-8"))


def test_proof_has_required_top_level_keys(proof: dict) -> None:
    missing = REQUIRED_TOP_KEYS - set(proof.keys())
    assert not missing, f"missing top-level keys: {sorted(missing)}"


def test_proof_lane_and_schema(proof: dict) -> None:
    assert proof["lane"] == "H3D-CLAUDE-SOURCE-PRINTFARM"
    assert proof["schema"] == "hermes3d://proof/printfarm_verify/v1"
    assert proof["tool"] == "verify_printfarm.py"


def test_policy_block_is_strict_read_only(proof: dict) -> None:
    policy = proof["policy"]
    assert policy["read_only"] is True
    assert policy["no_post"] is True
    assert policy["no_gcode_upload"] is True
    assert policy["s1_camera_skipped"] is True
    assert policy["timeout_seconds"] <= 2.0


def test_printers_match_expected_fleet(proof: dict) -> None:
    names = {p["name"] for p in proof["printers"]}
    assert names == EXPECTED_PRINTER_NAMES, f"unexpected printer set: {names}"


def test_each_printer_entry_has_required_keys(proof: dict) -> None:
    for printer in proof["printers"]:
        missing = REQUIRED_PRINTER_KEYS - set(printer.keys())
        assert not missing, f"printer {printer.get('name')} missing keys: {sorted(missing)}"


def test_s1_is_skipped_and_never_probed(proof: dict) -> None:
    s1 = next(p for p in proof["printers"] if p["name"] == "flsun_s1_camera")
    assert s1["skipped"] is True
    assert s1["reachable"] is None
    assert s1["url"] is None
    assert s1["method"] is None
    assert s1["policy"] == "camera-read-only-skipped"


def test_moonraker_printers_use_get_only(proof: dict) -> None:
    moonraker = [p for p in proof["printers"] if p["service"] == "moonraker"]
    assert moonraker, "expected at least one moonraker printer"
    for printer in moonraker:
        assert printer["skipped"] is False
        assert printer["method"] in (None, "GET"), f"non-GET method on {printer['name']}"
        assert printer["url"] is not None
        assert printer["url"].endswith("/server/info"), f"unexpected url on {printer['name']}: {printer['url']}"
        assert printer["port"] == 7125
        assert isinstance(printer["reachable"], bool)


def test_services_present_and_get_only(proof: dict) -> None:
    services = {s["service"]: s for s in proof["services"]}
    assert set(services.keys()) == EXPECTED_SERVICES
    for entry in services.values():
        missing = REQUIRED_SERVICE_KEYS - set(entry.keys())
        assert not missing, f"service {entry.get('service')} missing keys: {sorted(missing)}"
        assert entry["method"] in (None, "GET")
        assert isinstance(entry["reachable"], bool)


def test_summary_consistency(proof: dict) -> None:
    summary = proof["summary"]
    printers = proof["printers"]
    services = proof["services"]
    assert summary["printers_total"] == len(printers)
    assert summary["printers_skipped"] == sum(1 for p in printers if p.get("skipped"))
    assert summary["printers_reachable"] == sum(1 for p in printers if p.get("reachable") is True)
    assert summary["printers_unreachable"] == sum(1 for p in printers if p.get("reachable") is False)
    assert summary["services_total"] == len(services)
    assert summary["services_reachable"] == sum(1 for s in services if s.get("reachable") is True)
    assert summary["services_unreachable"] == sum(1 for s in services if s.get("reachable") is False)
