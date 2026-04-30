"""Integration tests for the A.6 proof-bundle pipeline.

Each test:
  1. builds a bundle into a tmp_path
  2. invokes ``05_truth_proof/conformance_runner.py --bundle <zip>``
     as a subprocess
  3. asserts the appropriate exit code / error string

The build script is invoked in-process (via ``scripts/_build_bundle.py``)
to keep tests fast and OS-portable.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

# Skip cleanly if matplotlib import would break collection (rubric requirement).
matplotlib_spec = importlib.util.find_spec("matplotlib")
pytestmark = pytest.mark.skipif(
    matplotlib_spec is None,
    reason="matplotlib not installed; bundle build pipeline depends on UI deps",
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "_build_bundle.py"
RUNNER = REPO_ROOT / "05_truth_proof" / "conformance_runner.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("_build_bundle", BUILD_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _build(tmp_path: Path, key: str) -> Path:
    os.environ["HERMES3D_PROOF_KEY"] = key
    builder = _load_builder()
    # Stub out heavy work to keep the test fast.
    builder.run_pytest = lambda work: (None, "")  # type: ignore[attr-defined]
    builder.run_forbidden_scan = lambda work: work / "logs" / "forbidden_scan.log"  # type: ignore[attr-defined]
    out_dir = tmp_path / "bundles"
    info = builder.build(out_dir, "HERMES3D_PROOF_KEY")
    return Path(info["path"])


def _verify(zip_path: Path, key: str) -> tuple[int, str]:
    env = os.environ.copy()
    env["HERMES3D_PROOF_KEY"] = key
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--bundle", str(zip_path), "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_bundle_round_trips(tmp_path: Path):
    """Build → verify with the same key returns 0."""
    key = "test-key-roundtrip"
    bundle = _build(tmp_path, key)
    assert bundle.is_file()
    assert bundle.stat().st_size > 0
    rc, out = _verify(bundle, key)
    assert rc == 0, f"verifier failed: {out}"
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["errors"] == []


def test_bundle_signature_tampered(tmp_path: Path):
    """Mutating manifest.json after signing must fail the signature check."""
    key = "test-key-tamper"
    bundle = _build(tmp_path, key)

    # Rewrite the zip with a mutated manifest.json (bump duration).
    tampered = tmp_path / "tampered.zip"
    with (
        zipfile.ZipFile(bundle, "r") as src,
        zipfile.ZipFile(tampered, "w", zipfile.ZIP_DEFLATED) as dst,
    ):
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "manifest.json":
                m = json.loads(data.decode("utf-8"))
                m["build"]["duration_seconds"] = 999999.0
                data = json.dumps(m, sort_keys=True, separators=(",", ":")).encode("utf-8")
            dst.writestr(item, data)

    rc, out = _verify(tampered, key)
    assert rc != 0
    assert "signature" in out.lower()


def test_bundle_missing_file(tmp_path: Path):
    """Removing a manifest-listed file must fail with missing-file error."""
    key = "test-key-missing"
    bundle = _build(tmp_path, key)

    # Find a file other than manifest.* to drop.
    with zipfile.ZipFile(bundle, "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        names = set(zf.namelist())

    droppable = next(
        (
            e["path"]
            for e in manifest["files"]
            if e["path"] not in ("manifest.json", "manifest.sig") and e["path"] in names
        ),
        None,
    )
    assert droppable is not None, "bundle had no droppable file — fixture broken"

    pruned = tmp_path / "pruned.zip"
    with (
        zipfile.ZipFile(bundle, "r") as src,
        zipfile.ZipFile(pruned, "w", zipfile.ZIP_DEFLATED) as dst,
    ):
        for item in src.infolist():
            if item.filename == droppable:
                continue
            dst.writestr(item, src.read(item.filename))

    rc, out = _verify(pruned, key)
    assert rc != 0
    assert "missing-file" in out
