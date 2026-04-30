"""Print farm dashboard — fleet-wide live aggregation.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §16 (Print Farm Dashboard)

Aggregates live state across all 12 printers in the fleet for display in
the Gradio UI. This is a read-only data layer — it never mutates printer
state. It composes:

    moonraker_client.probe_fleet()  -> reachability + klippy state
    job_queue.JobQueue              -> active jobs per printer
    spool_tracker.SpoolTracker      -> filament loaded + remaining
    printers.FLEET                  -> static profile data

Returns a list of FleetEntry rows ready for table rendering.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from hermes3d.core.printers import FLEET, PrinterProfile
from hermes3d.core.printers.moonraker_client import probe_fleet
from hermes3d.core.agents.job_queue import Job, JobQueue, JobState


@dataclass
class FleetEntry:
    """One row in the dashboard table."""

    profile_id: str
    manufacturer: str
    model: str
    kinematics: str
    bed_descr: str
    z_height_mm: float
    moonraker_url: str
    reachable: bool
    klippy_state: str | None
    moonraker_version: str | None
    error: str | None
    active_job_id: str | None = None
    active_job_state: str | None = None
    loaded_spool_id: str | None = None
    loaded_spool_label: str | None = None
    loaded_spool_remaining_g: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _bed_descr(p: PrinterProfile) -> str:
    if p.bed.kind == "rectangular":
        return f"{p.bed.x_mm:.0f}×{p.bed.y_mm:.0f} mm"
    return f"Ø{p.bed.diameter_mm:.0f} mm"


def collect_fleet_status(
    *,
    queue: JobQueue | None = None,
    spool_tracker: Any | None = None,  # SpoolTracker, kept loose for testability
    timeout_s: float = 2.5,
) -> list[FleetEntry]:
    """Build a fleet status snapshot.

    All optional parameters are dependency-injected so tests can pass mock
    queues / trackers / live data.
    """
    # Live network probe
    probe = {p["profile_id"]: p for p in probe_fleet(timeout_s=timeout_s)}

    # Active jobs per printer (in-flight states)
    active_states = {
        JobState.DISPATCHED,
        JobState.VALIDATED,
        JobState.SLICED,
        JobState.UPLOADED,
        JobState.PRINTING,
    }
    jobs_by_printer: dict[str, Job] = {}
    if queue is not None:
        for job in queue.list():
            if job.state in active_states and job.target_printer_id:
                # Latest active job per printer wins
                existing = jobs_by_printer.get(job.target_printer_id)
                if existing is None or job.updated_unix > existing.updated_unix:
                    jobs_by_printer[job.target_printer_id] = job

    out: list[FleetEntry] = []
    for p in FLEET:
        live = probe.get(p.profile_id, {})
        entry = FleetEntry(
            profile_id=p.profile_id,
            manufacturer=p.manufacturer,
            model=p.model,
            kinematics=p.kinematics.value,
            bed_descr=_bed_descr(p),
            z_height_mm=p.z_height_mm,
            moonraker_url=p.moonraker_url_default,
            reachable=bool(live.get("reachable", False)),
            klippy_state=live.get("klippy_state"),
            moonraker_version=live.get("moonraker_version"),
            error=live.get("error"),
        )
        if j := jobs_by_printer.get(p.profile_id):
            entry.active_job_id = j.job_id
            entry.active_job_state = j.state.value
        if spool_tracker is not None:
            spools = spool_tracker.list(printer_id=p.profile_id)
            if spools:
                s = spools[-1]  # most recent
                entry.loaded_spool_id = s.spool_id
                entry.loaded_spool_label = f"{s.vendor} {s.material} {s.color}"
                entry.loaded_spool_remaining_g = s.remaining_grams
        out.append(entry)
    return out


def render_dashboard_table(entries: list[FleetEntry]) -> str:
    """Render entries as an aligned plain-text table for CLI / logs."""
    if not entries:
        return "(no printers)"
    cols = (
        ("Printer", lambda e: f"{e.profile_id}"),
        ("Make/Model", lambda e: f"{e.manufacturer} {e.model}"),
        ("Kin.", lambda e: e.kinematics),
        ("Bed", lambda e: e.bed_descr),
        ("Z", lambda e: f"{e.z_height_mm:.0f}mm"),
        ("Reach", lambda e: "✓" if e.reachable else "—"),
        ("State", lambda e: e.klippy_state or "—"),
        ("Job", lambda e: (e.active_job_state or "idle")),
        ("Spool", lambda e: e.loaded_spool_label or "—"),
    )
    rows = [[hd for hd, _ in cols]]
    for e in entries:
        rows.append([str(fn(e)) for _, fn in cols])
    widths = [max(len(r[i]) for r in rows) for i in range(len(cols))]
    lines = []
    for ri, r in enumerate(rows):
        line = "  ".join(c.ljust(widths[i]) for i, c in enumerate(r))
        lines.append(line)
        if ri == 0:
            lines.append("  ".join("-" * widths[i] for i in range(len(cols))))
    return "\n".join(lines)


__all__ = [
    "FleetEntry",
    "collect_fleet_status",
    "render_dashboard_table",
]
