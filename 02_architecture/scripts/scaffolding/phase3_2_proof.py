#!/usr/bin/env python3
"""Assemble the Phase 3.2 planner + DAG proof bundle.

The bundle is evidence-only: it snapshots the plan/ADR, an offline ledger with
planner.plan events, deterministic plan-preview replay data, UI build hashes,
the Playwright JSON report, and deterministic DAG fixture replay data. It also
verifies that the sidecar manifest exactly matches the zip contents.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import sys
import tempfile
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "06_release" / "phase3.2-bundle"
DIST_DIR = REPO_ROOT / "03_implementation" / "ui" / "dist"

REQUIRED_DOCS = {
    "docs/PHASE3_2_PLAN.md": REPO_ROOT / "00_overview" / "PHASE3_2_PLAN.md",
    "docs/ADR-010-planner-and-dag.md": REPO_ROOT
    / "02_architecture"
    / "adr"
    / "ADR-010-planner-and-dag.md",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--playwright-json", type=Path, required=True)
    args = parser.parse_args()

    run_id = args.run_id or _default_run_id()
    bundle_dir = OUTPUT_DIR
    bundle_dir.mkdir(parents=True, exist_ok=True)

    zip_path = bundle_dir / f"{run_id}.zip"
    manifest_path = bundle_dir / f"{run_id}.manifest.json"
    sha_path = bundle_dir / f"{run_id}.sha256"

    with tempfile.TemporaryDirectory(prefix=f"{run_id}-") as tmp:
        staging = Path(tmp)
        entries: dict[str, Path] = {}
        for archive_name, source in REQUIRED_DOCS.items():
            _require_file(source)
            entries[archive_name] = source

        ledger_snapshot = staging / "ledger_snapshot.sqlite3"
        plan_preview_replay = staging / "plan_preview_replay.json"
        dag_fixture_replay = staging / "dag_fixture_replay.json"
        _write_phase32_replay(
            ledger_snapshot=ledger_snapshot,
            plan_preview_replay=plan_preview_replay,
            dag_fixture_replay=dag_fixture_replay,
        )
        entries["evidence/ledger_snapshot.sqlite3"] = ledger_snapshot
        entries["evidence/plan_preview_replay.json"] = plan_preview_replay
        entries["evidence/dag_fixture_replay.json"] = dag_fixture_replay

        ui_hashes = staging / "ui_build_output_hash.json"
        _write_ui_build_hashes(ui_hashes)
        entries["evidence/ui_build_output_hash.json"] = ui_hashes

        playwright_json = args.playwright_json.resolve()
        _require_file(playwright_json)
        entries["evidence/playwright_report.json"] = playwright_json

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for archive_name in sorted(entries):
                zf.write(entries[archive_name], archive_name)

        manifest = _build_manifest(run_id, zip_path)
        manifest_path.write_text(_canonical_json(manifest), encoding="utf-8")
        digest = _sha256_file(zip_path)
        sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")

    verified = verify_bundle(zip_path, manifest_path)
    print(
        json.dumps(
            {
                "bundle": str(zip_path.relative_to(REPO_ROOT)),
                "manifest": str(manifest_path.relative_to(REPO_ROOT)),
                "sha256": digest,
                "verified": verified,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def verify_bundle(zip_path: Path, manifest_path: Path) -> bool:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {entry["path"]: entry for entry in manifest["files"]}
    with zipfile.ZipFile(zip_path, "r") as zf:
        actual_names = sorted(info.filename for info in zf.infolist())
        if actual_names != sorted(expected):
            missing = sorted(set(expected) - set(actual_names))
            extra = sorted(set(actual_names) - set(expected))
            raise RuntimeError(f"manifest mismatch: missing={missing}, extra={extra}")
        for name in actual_names:
            data = zf.read(name)
            digest = hashlib.sha256(data).hexdigest()
            size = len(data)
            expected_entry = expected[name]
            if digest != expected_entry["sha256"] or size != expected_entry["size"]:
                raise RuntimeError(f"manifest hash/size mismatch for {name}")
    return True


def _write_phase32_replay(
    *,
    ledger_snapshot: Path,
    plan_preview_replay: Path,
    dag_fixture_replay: Path,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "03_implementation" / "src"))
    from hermes3d.agents.planner import PlannerAgent
    from hermes3d.orchestration import OfflineSupervisor, Ok, OrchestrationLedger, PlanRequest
    from hermes3d.orchestration.bridge import BridgeState, serialize_dag

    ledger = OrchestrationLedger(ledger_snapshot)
    state = BridgeState(ledger=ledger)
    preview_dag = state.preview_plan("calibration cube")
    preview_events = ledger.events(preview_dag["run_id"])

    plan_preview_replay.write_text(
        _canonical_json(
            {
                "route": "POST /api/plan/preview",
                "request": {"prompt": "calibration cube"},
                "response": preview_dag,
                "ledger_tools": [event.tool for event in preview_events],
                "gen3d_generate_events": sum(
                    1 for event in preview_events if event.tool == "gen3d.generate"
                ),
            }
        ),
        encoding="utf-8",
    )

    supervisor = OfflineSupervisor(ledger=ledger)
    planner = PlannerAgent(supervisor=supervisor)
    fixtures: list[dict[str, object]] = []
    for prompt in ("calibration cube", "mini vase"):
        token = supervisor.issue_token(
            agent_id="proof.fixture.planner",
            tools=frozenset({"planner.plan"}),
        )
        result = planner.plan(
            PlanRequest(
                run_id=f"dag-fixture-{stable_prompt_id(prompt)}",
                agent_id="proof.fixture.planner",
                prompt=prompt,
            ),
            token=token,
        )
        if not isinstance(result.result, Ok):
            raise RuntimeError(f"fixture prompt failed: {prompt}: {result.result}")
        dag_payload = serialize_dag(result.result.value)
        fixtures.append(
            {
                "prompt": prompt,
                "dag": dag_payload,
                "dag_sha256": hashlib.sha256(
                    _canonical_json(dag_payload).encode("utf-8")
                ).hexdigest(),
            }
        )

    dag_fixture_replay.write_text(
        _canonical_json(
            {
                "planner": "deterministic-template",
                "fixtures": fixtures,
            }
        ),
        encoding="utf-8",
    )
    gc.collect()


def stable_prompt_id(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


def _write_ui_build_hashes(path: Path) -> None:
    if not DIST_DIR.exists():
        raise FileNotFoundError(f"UI dist not found; run npm run build first: {DIST_DIR}")
    files: list[dict[str, Any]] = []
    for file_path in sorted(p for p in DIST_DIR.rglob("*") if p.is_file()):
        files.append(
            {
                "path": str(file_path.relative_to(DIST_DIR)).replace("\\", "/"),
                "sha256": _sha256_file(file_path),
                "size": file_path.stat().st_size,
            }
        )
    rollup = hashlib.sha256(_canonical_json(files).encode("utf-8")).hexdigest()
    path.write_text(_canonical_json({"dist": files, "rollup_sha256": rollup}), encoding="utf-8")


def _build_manifest(run_id: str, zip_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        files = [
            {
                "path": info.filename,
                "sha256": hashlib.sha256(zf.read(info.filename)).hexdigest(),
                "size": info.file_size,
            }
            for info in sorted(zf.infolist(), key=lambda item: item.filename)
        ]
    return {
        "schema_version": "phase3.2-bundle-1.0.0",
        "run_id": run_id,
        "created_utc": datetime.now(UTC).isoformat(),
        "git": _git_metadata(),
        "env": {
            "python": platform.python_version(),
            "python_impl": platform.python_implementation(),
            "os": platform.platform(),
            "machine": platform.machine(),
        },
        "files": files,
    }


def _git_metadata() -> dict[str, Any]:
    branch, sha = _read_git_head()
    return {
        "branch": branch,
        "sha": sha,
        "dirty": "not-computed",
    }


def _default_run_id() -> str:
    _branch, sha = _read_git_head()
    return f"{sha[:12]}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"


def _read_git_head() -> tuple[str, str]:
    git_dir = REPO_ROOT / ".git"
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return "detached", head

    ref = head.removeprefix("ref: ").strip()
    ref_path = git_dir / ref
    if ref_path.exists():
        sha = ref_path.read_text(encoding="utf-8").strip()
    else:
        sha = _read_packed_ref(git_dir / "packed-refs", ref)
    branch = ref.removeprefix("refs/heads/")
    return branch, sha


def _read_packed_ref(path: Path, ref: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Git ref not found: {ref}")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or line.startswith("^") or not line.strip():
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        sha, packed_ref = parts
        if packed_ref == ref:
            return sha
    raise FileNotFoundError(f"Git ref not found in packed-refs: {ref}")


def _require_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), indent=2, sort_keys=True) + "\n"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
