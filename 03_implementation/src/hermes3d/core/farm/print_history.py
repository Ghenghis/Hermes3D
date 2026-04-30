"""Print history + metrics collector.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §20 (Print History)

Records the outcome of every print job: which printer, material, duration,
filament used, success/failure. The data is persisted as JSONL (one JSON
record per line) so it can be tailed/streamed and never corrupts on
partial writes.

Two pieces:
  - PrintHistory: append-only log of finished prints
  - aggregate_metrics(): computes per-printer reliability, per-material
    success rate, total filament consumed, total print hours

The dispatcher's "least-busy" and future ML-driven scoring strategies can
read these aggregates to bias selection — e.g. avoid the printer with a
70% recent failure rate.
"""

from __future__ import annotations

import dataclasses
import json
import threading
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class PrintRecord:
    """A single completed print event (success OR failure).

    Append-only — once written, never modified. Edit-style corrections
    are made by appending a *new* record with ``correction_of`` set.
    """

    record_id: str
    job_id: str
    printer_id: str
    material: str
    started_unix: float
    ended_unix: float
    success: bool
    filament_used_g: float | None = None
    filament_used_mm: float | None = None
    layer_count: int | None = None
    layer_height_mm: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    error: str | None = None
    cancelled_reason: str | None = None
    spool_id: str | None = None
    notes: str = ""
    correction_of: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_min(self) -> float:
        return max(0.0, (self.ended_unix - self.started_unix) / 60.0)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PrintRecord:
        return cls(**d)


# =============================================================================


class PrintHistory:
    """Append-only JSONL log of completed prints."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    def append(
        self,
        *,
        job_id: str,
        printer_id: str,
        material: str,
        started_unix: float,
        ended_unix: float,
        success: bool,
        **kwargs: Any,
    ) -> PrintRecord:
        record = PrintRecord(
            record_id=uuid.uuid4().hex,
            job_id=job_id,
            printer_id=printer_id,
            material=material,
            started_unix=started_unix,
            ended_unix=ended_unix,
            success=success,
            **kwargs,
        )
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "record": record.to_dict(),
                            "appended_unix": time.time(),
                        }
                    )
                    + "\n"
                )
        return record

    def iter_records(self) -> Iterable[PrintRecord]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    yield PrintRecord.from_dict(obj["record"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Skip corrupt lines but keep the rest readable
                    continue

    def list(self) -> list[PrintRecord]:
        return list(self.iter_records())


# =============================================================================
# Aggregations
# =============================================================================


@dataclass
class PrinterAggregate:
    printer_id: str
    total_prints: int = 0
    successful: int = 0
    failed: int = 0
    cancelled: int = 0
    total_print_minutes: float = 0.0
    total_filament_grams: float = 0.0

    @property
    def success_rate(self) -> float:
        attempts = self.successful + self.failed
        return self.successful / attempts if attempts else 0.0


@dataclass
class MaterialAggregate:
    material: str
    total_prints: int = 0
    successful: int = 0
    total_filament_grams: float = 0.0


@dataclass
class FleetMetrics:
    per_printer: dict[str, PrinterAggregate] = field(default_factory=dict)
    per_material: dict[str, MaterialAggregate] = field(default_factory=dict)
    total_prints: int = 0
    total_print_hours: float = 0.0
    total_filament_kg: float = 0.0
    window_start_unix: float | None = None
    window_end_unix: float | None = None


def aggregate_metrics(
    history: PrintHistory, *, since_unix: float | None = None, until_unix: float | None = None
) -> FleetMetrics:
    metrics = FleetMetrics()
    earliest = None
    latest = None
    for r in history.iter_records():
        if since_unix is not None and r.started_unix < since_unix:
            continue
        if until_unix is not None and r.started_unix > until_unix:
            continue
        earliest = r.started_unix if earliest is None else min(earliest, r.started_unix)
        latest = r.ended_unix if latest is None else max(latest, r.ended_unix)
        metrics.total_prints += 1

        pa = metrics.per_printer.setdefault(r.printer_id, PrinterAggregate(printer_id=r.printer_id))
        pa.total_prints += 1
        if r.success:
            pa.successful += 1
        elif r.cancelled_reason:
            pa.cancelled += 1
        else:
            pa.failed += 1
        pa.total_print_minutes += r.duration_min
        if r.filament_used_g:
            pa.total_filament_grams += r.filament_used_g

        ma = metrics.per_material.setdefault(
            r.material.upper(), MaterialAggregate(material=r.material.upper())
        )
        ma.total_prints += 1
        if r.success:
            ma.successful += 1
        if r.filament_used_g:
            ma.total_filament_grams += r.filament_used_g

        metrics.total_print_hours += r.duration_min / 60.0
        if r.filament_used_g:
            metrics.total_filament_kg += r.filament_used_g / 1000.0

    metrics.window_start_unix = earliest
    metrics.window_end_unix = latest
    return metrics


__all__ = [
    "SCHEMA_VERSION",
    "FleetMetrics",
    "MaterialAggregate",
    "PrintHistory",
    "PrintRecord",
    "PrinterAggregate",
    "aggregate_metrics",
]
