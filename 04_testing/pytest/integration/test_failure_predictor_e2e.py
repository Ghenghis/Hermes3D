from __future__ import annotations

import time
from pathlib import Path

import pytest


def test_failure_predictor_reads_seeded_print_history_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hermes3d.core.farm.print_history import PrintHistory
    from hermes3d.core.intelligence.failure_predictor import predict_failure

    history_path = tmp_path / "print_history.jsonl"
    history = PrintHistory(history_path)
    started = time.time() - 20_000
    for index in range(10):
        history.append(
            job_id=f"calibration-cube-{index}",
            printer_id="flsun_t1_a",
            material="PLA",
            started_unix=started + index * 1200,
            ended_unix=started + index * 1200 + 600,
            success=index >= 3,
        )

    monkeypatch.setenv("HERMES3D_PRINT_HISTORY", str(history_path))

    forecast = predict_failure(printer_id="flsun_t1_a", material="PLA")

    assert forecast.failure_probability == pytest.approx(0.20, abs=0.001)
    assert forecast.confidence == "medium"
    assert forecast.components == {
        "printer_history": 0.3,
        "material_history": 0.3,
        "baseline": 0.1,
    }
    assert forecast.citations == [
        "PrintHistory[flsun_t1_a]: 3 fails / 10 attempts",
        "PrintHistory[material=PLA]: 7/10 successful",
    ]
