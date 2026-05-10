from __future__ import annotations

import hashlib
import json
import struct
import subprocess
from pathlib import Path

import pytest
from hermes3d.core.slicer.slicer_runner import parse_gcode_metadata
from hermes3d.services import rust_accel


def test_file_sha256_falls_back_when_accelerator_missing(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "payload.bin"
    target.write_bytes(b"hermes3d-rust-accel")
    monkeypatch.setenv("HERMES3D_RUST_ACCEL_BIN", str(tmp_path / "missing.exe"))

    assert rust_accel.file_sha256_hex(target) == hashlib.sha256(target.read_bytes()).hexdigest()


def test_gcode_metadata_keeps_python_fallback_without_binary(tmp_path: Path, monkeypatch) -> None:
    gcode = tmp_path / "part.gcode"
    gcode.write_text(
        "; total layer count = 87\n"
        "; filament used [mm] = 4523.42\n"
        "; filament used [g] = 13.6\n"
        "; estimated printing time (normal mode) = 1h 23m 15s\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES3D_RUST_ACCEL_BIN", str(tmp_path / "missing.exe"))

    metadata = parse_gcode_metadata(gcode)
    assert metadata["estimated_minutes"] == pytest.approx(83.25, abs=0.01)
    assert metadata["estimated_filament_mm"] == pytest.approx(4523.42)
    assert metadata["estimated_filament_g"] == pytest.approx(13.6)
    assert metadata["layer_count"] == 87


def test_rust_binary_smoke_when_built(tmp_path: Path) -> None:
    binary = rust_accel.rust_accel_binary()
    if binary is None:
        pytest.skip("Rust acceleration binary is not built in this checkout")

    gcode = tmp_path / "part.gcode"
    gcode.write_text(
        "; num layers: 12\n; filament used [mm] = 100.5\n; estimated printing time = 00:02:30\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [str(binary), "gcode-meta", str(gcode)],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["source"] == "rust"
    assert payload["layer_count"] == 12
    assert payload["estimated_minutes"] == pytest.approx(2.5)


def test_rust_binary_stl_smoke_when_built(tmp_path: Path) -> None:
    binary = rust_accel.rust_accel_binary()
    if binary is None:
        pytest.skip("Rust acceleration binary is not built in this checkout")

    stl = tmp_path / "triangle.stl"
    with stl.open("wb") as fp:
        fp.write(b"\0" * 80)
        fp.write(struct.pack("<I", 1))
        fp.write(b"\0" * 12)
        for point in ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 20.0, 3.0)):
            fp.write(struct.pack("<fff", *point))
        fp.write(b"\0" * 2)

    proc = subprocess.run(
        [str(binary), "stl-meta", str(stl)],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["format"] == "binary_stl"
    assert payload["triangle_count"] == 1
    assert payload["extents_mm"] == [10.0, 20.0, 3.0]
