"""Filament spool tracker.

Status: runnable
Contract: 00-CONTRACT/MASTER_CONTRACT.md §15 (Filament Tracking)

Persistent JSON-backed registry of spools — what's loaded on which printer,
how much is left, vendor/material/color metadata. The dispatcher and
scheduler can use this to filter printers by available filament colour or
to warn when a print would deplete the loaded spool.
"""
from __future__ import annotations

import dataclasses
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"


@dataclass
class Spool:
    spool_id: str
    material: str            # e.g. "PLA", "PETG", "ABS"
    color: str               # human label, e.g. "matte black"
    color_hex: str           # "#1a1a1a"
    vendor: str              # e.g. "Polymaker", "eSun", "Prusament"
    diameter_mm: float       # 1.75 or 2.85
    initial_grams: float
    remaining_grams: float
    loaded_on_printer: str | None = None  # profile_id
    notes: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    created_unix: float = field(default_factory=time.time)
    updated_unix: float = field(default_factory=time.time)

    @property
    def percent_remaining(self) -> float:
        if self.initial_grams <= 0:
            return 0.0
        return max(0.0, min(100.0, 100.0 * self.remaining_grams / self.initial_grams))

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Spool":
        return cls(**d)


class SpoolTracker:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._spools: dict[str, Spool] = {}
        self._load()

    def _load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._spools = {}
                return
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(
                    f"Spool schema mismatch: got {data.get('schema_version')!r}, "
                    f"expected {SCHEMA_VERSION!r}"
                )
            self._spools = {s["spool_id"]: Spool.from_dict(s)
                            for s in data.get("spools", [])}

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "saved_unix": time.time(),
                "spools": [s.to_dict() for s in self._spools.values()],
            }
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, indent=2, sort_keys=True),
                           encoding="utf-8")
            os.replace(tmp, self.path)

    def add(self, *, material: str, color: str, color_hex: str,
            vendor: str, initial_grams: float,
            diameter_mm: float = 1.75, notes: str = "") -> Spool:
        with self._lock:
            now = time.time()
            spool = Spool(
                spool_id=uuid.uuid4().hex,
                material=material,
                color=color,
                color_hex=color_hex,
                vendor=vendor,
                diameter_mm=diameter_mm,
                initial_grams=float(initial_grams),
                remaining_grams=float(initial_grams),
                created_unix=now,
                updated_unix=now,
                notes=notes,
                history=[{"event": "registered", "at_unix": now,
                          "grams": initial_grams}],
            )
            self._spools[spool.spool_id] = spool
            self.save()
            return spool

    def get(self, spool_id: str) -> Spool:
        with self._lock:
            if spool_id not in self._spools:
                raise KeyError(spool_id)
            return self._spools[spool_id]

    def list(self, *, printer_id: str | None = None,
             material: str | None = None) -> list[Spool]:
        with self._lock:
            out = list(self._spools.values())
            if printer_id is not None:
                out = [s for s in out if s.loaded_on_printer == printer_id]
            if material is not None:
                out = [s for s in out if s.material.upper() == material.upper()]
            return sorted(out, key=lambda s: s.updated_unix)

    def load_on_printer(self, spool_id: str, printer_id: str) -> Spool:
        with self._lock:
            # Unload any existing spool on this printer first
            for s in self._spools.values():
                if s.loaded_on_printer == printer_id and s.spool_id != spool_id:
                    s.loaded_on_printer = None
                    s.updated_unix = time.time()
                    s.history.append({"event": "unloaded", "from": printer_id,
                                      "at_unix": s.updated_unix})
            spool = self.get(spool_id)
            spool.loaded_on_printer = printer_id
            spool.updated_unix = time.time()
            spool.history.append({"event": "loaded", "on": printer_id,
                                  "at_unix": spool.updated_unix})
            self.save()
            return spool

    def consume(self, spool_id: str, grams: float, *,
                job_id: str | None = None) -> Spool:
        if grams < 0:
            raise ValueError("grams must be non-negative")
        with self._lock:
            spool = self.get(spool_id)
            spool.remaining_grams = max(0.0, spool.remaining_grams - grams)
            spool.updated_unix = time.time()
            spool.history.append({
                "event": "consumed",
                "grams": grams,
                "remaining": spool.remaining_grams,
                "job_id": job_id,
                "at_unix": spool.updated_unix,
            })
            self.save()
            return spool

    def find_for_material(self, material: str, *,
                          loaded_only: bool = False) -> list[Spool]:
        out = self.list(material=material)
        if loaded_only:
            out = [s for s in out if s.loaded_on_printer is not None]
        return [s for s in out if s.remaining_grams > 0]


__all__ = ["Spool", "SpoolTracker", "SCHEMA_VERSION"]
