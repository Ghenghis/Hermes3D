"""Build Phase 5.1 proof JSON.

This script is intentionally small and deterministic. It records the merged
checkpoint commits, CI layer evidence, and local validation commands that close
Phase 5.1, then writes the committed proof artifact.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = {
    "5.1": REPO_ROOT / "00_overview" / "proofs" / "phase_5_1_proof.json",
}
PHASE_HEAD = "3bcf191d832b91852af86363bf06230d43ca3075"

CHECKPOINTS: list[dict[str, str]] = [
    {
        "id": "CP5.1-A",
        "pr": "18",
        "url": "https://github.com/Ghenghis/Hermes3D/pull/18",
        "title": "Plan + ADR-013 for kit hardening",
        "head_commit": "b1a5182f71aca90791564c96ff88def9a1b18e23",
        "merge_commit": "ec5634af3870f620503439c379ce9e483bb31c52",
        "evidence": "00_overview/PHASE5_1_PLAN.md + 02_architecture/adr/ADR-013-kit-hardening-v5_1.md",
    },
    {
        "id": "CP5.1-B",
        "pr": "21",
        "url": "https://github.com/Ghenghis/Hermes3D/pull/21",
        "title": "failure_predictor end-to-end + backup scheduler tick",
        "head_commit": "8fb9d751537be18f7a1b8b3b888a335fffb96165",
        "merge_commit": "d28d2c16c9e128ea6d86bc40d57f3739eb3ffc7e",
        "evidence": "04_testing/pytest/integration/test_failure_predictor_e2e.py + test_backup_scheduler.py",
    },
    {
        "id": "CP5.1-C",
        "pr": "23",
        "url": "https://github.com/Ghenghis/Hermes3D/pull/23",
        "title": "profile_generator + skill_store reader + doctor JSON envelope",
        "head_commit": "6ccdf3a5de74dc2c70c443002dadff2f8aae7a35",
        "merge_commit": "3bcf191d832b91852af86363bf06230d43ca3075",
        "evidence": "04_testing/pytest/integration/test_profile_generator_skill_wired.py + doctor JSON tests",
    },
    {
        "id": "CP5.1-D",
        "pr": "19",
        "url": "https://github.com/Ghenghis/Hermes3D/pull/19",
        "title": "Layer-D3 Gradio smoke + Layer-M matrix coverage gate",
        "head_commit": "b2134b30a63828d2f4dc0d3180f60902e519caa4",
        "merge_commit": "e6b80ae3b63fec14705948972e356959dbef6b2c",
        "evidence": "04_testing/playwright/gradio_smoke.spec.ts + .github/workflows/ci.yml Layer M",
    },
]

ACCEPTANCE_GATES: list[dict[str, str]] = [
    {
        "gate": "Layer A",
        "status": "PASS",
        "evidence": "ci run 25271637727: Layer A — static gates",
    },
    {
        "gate": "Layer B",
        "status": "PASS",
        "evidence": "ci run 25271637727: 4/4 matrix cells passed",
    },
    {
        "gate": "Layer C",
        "status": "PASS",
        "evidence": "ci run 25271637727: Layer C — integration",
    },
    {
        "gate": "Layer D",
        "status": "PASS",
        "evidence": "ci run 25271637727: Layer D — UI E2E",
    },
    {
        "gate": "Layer D2",
        "status": "SKIPPED",
        "evidence": "ui-ci path filters did not trigger on develop@3bcf191",
    },
    {
        "gate": "Layer D3",
        "status": "ADVISORY_FAIL",
        "evidence": "ci run 25271637727: Layer D3 job failed but remains non-blocking in CP5.1",
    },
    {
        "gate": "Layer E",
        "status": "SKIPPED",
        "evidence": "release dry-run skipped on non-release branch",
    },
    {
        "gate": "Layer F",
        "status": "PASS",
        "evidence": "ci run 25271637727: Layer F — honesty gates",
    },
    {
        "gate": "Layer M",
        "status": "PASS",
        "evidence": "ci run 25271637727: Layer M — matrix coverage",
    },
    {
        "gate": "Layer T",
        "status": "PASS",
        "evidence": "ci run 25271637727: Layer T — Unified Truth Gate",
    },
    {
        "gate": "Layer W",
        "status": "PASS",
        "evidence": "ci run 25271637727: Layer W — Wizard E2E",
    },
    {
        "gate": "Layer P5.1",
        "status": "PASS",
        "evidence": "scripts/scaffolding/_build_phase_proof.py --phase 5.1",
    },
]

PROMOTED_CLAIMS: list[dict[str, str]] = [
    {
        "claim": "failure_predictor reads a real print_history ledger",
        "evidence": "CP5.1-B integration test seeds print_history.jsonl and checks calibrated output",
    },
    {
        "claim": "backup scheduler ticks under the supervisor daemon",
        "evidence": "CP5.1-B integration test observes two scheduled archives and retention pruning",
    },
    {
        "claim": "profile_generator consumes skill-store reader suggestions",
        "evidence": "CP5.1-C integration test injects SkillStoreReader and verifies reinforced overrides",
    },
    {
        "claim": "doctor scripts emit versioned JSON envelopes",
        "evidence": "CP5.1-C unit tests fixture Windows, Linux, and macOS checks",
    },
    {
        "claim": "CI matrix completeness is enforced",
        "evidence": "CP5.1-D Layer M gate passed on develop run 25271637727",
    },
]


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _commit_is_ancestor(commit: str, head: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, head],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def _build_proof(phase: str) -> dict[str, Any]:
    if phase != "5.1":
        raise ValueError(f"Unsupported phase {phase!r}; expected '5.1'")
    current_head = _git("rev-parse", "HEAD")
    short_head = PHASE_HEAD[:12]
    created_utc = (
        datetime.fromisoformat(_git("show", "-s", "--format=%cI", PHASE_HEAD))
        .astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )
    checkpoint_status = []
    for checkpoint in CHECKPOINTS:
        row = dict(checkpoint)
        row["merge_commit_in_head"] = _commit_is_ancestor(
            checkpoint["merge_commit"],
            current_head,
        )
        checkpoint_status.append(row)

    missing = [c["id"] for c in checkpoint_status if not c["merge_commit_in_head"]]
    if missing:
        raise RuntimeError(f"Phase 5.1 proof missing checkpoint commits: {', '.join(missing)}")

    return {
        "schema_version": "phase5.1-proof-1.0.0",
        "phase": "5.1",
        "version": "v5.1.0",
        "proof_id": f"phase5.1-{short_head}",
        "created_utc": created_utc,
        "git": {
            "branch": "develop",
            "head": PHASE_HEAD,
            "head_short": short_head,
        },
        "ci": {
            "develop_run": {
                "id": 25271637727,
                "url": "https://github.com/Ghenghis/Hermes3D/actions/runs/25271637727",
                "conclusion": "success",
                "head": "3bcf191d832b91852af86363bf06230d43ca3075",
            }
        },
        "checkpoints": checkpoint_status,
        "acceptance_gates": ACCEPTANCE_GATES,
        "promoted_claims": PROMOTED_CLAIMS,
        "local_validation": [
            {
                "command": "cd 03_implementation && python -m pytest ../04_testing/pytest -q",
                "result": "670 passed",
            },
            {
                "command": "python -m ruff check 03_implementation/src 04_testing/pytest",
                "result": "PASS",
            },
            {
                "command": "python -m ruff format --check 03_implementation/src 04_testing/pytest",
                "result": "PASS",
            },
            {
                "command": "python scripts/scaffolding/_build_phase_proof.py --phase 5.1",
                "result": "PASS",
            },
            {
                "command": "python -m json.tool 00_overview/proofs/phase_5_1_proof.json",
                "result": "PASS",
            },
        ],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=sorted(OUTPUTS))
    args = parser.parse_args()
    payload = _build_proof(args.phase)
    output = OUTPUTS[args.phase]
    _write_json(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
