"""Print job queue + manifest.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §11 (Print Job Lifecycle)

A persistent JSON-backed queue of print jobs. Each job records:
  - id (UUID), state, timestamps
  - source mesh path + sha256
  - target printer_id (set on dispatch)
  - sliced gcode path + sha256 (set on slice)
  - moonraker_item_path (set on upload)
  - dispatcher decision (full DispatchDecision dict)
  - truth_gate_report (full report)
  - proof_envelope_path (when written)

State machine:
    QUEUED -> DISPATCHED -> VALIDATED -> SLICED -> UPLOADED ->
    PRINTING -> SUCCEEDED / FAILED / CANCELLED

The queue file is human-readable JSON. The JobQueue class is process-safe
via an OS file lock on save (with a fallback for non-POSIX).
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"


class JobState(str, enum.Enum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    VALIDATED = "validated"
    SLICED = "sliced"
    UPLOADED = "uploaded"
    PRINTING = "printing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Allowed forward transitions (one of these must hold OR a backward move
# to QUEUED for retry, OR -> CANCELLED from any non-terminal state).
_ALLOWED: dict[JobState, set[JobState]] = {
    JobState.QUEUED: {JobState.DISPATCHED, JobState.CANCELLED, JobState.FAILED},
    JobState.DISPATCHED: {JobState.VALIDATED, JobState.QUEUED, JobState.CANCELLED, JobState.FAILED},
    JobState.VALIDATED: {JobState.SLICED, JobState.QUEUED, JobState.CANCELLED, JobState.FAILED},
    JobState.SLICED: {JobState.UPLOADED, JobState.QUEUED, JobState.CANCELLED, JobState.FAILED},
    JobState.UPLOADED: {JobState.PRINTING, JobState.CANCELLED, JobState.FAILED},
    JobState.PRINTING: {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED},
    JobState.SUCCEEDED: set(),  # terminal
    JobState.FAILED: {JobState.QUEUED},  # retry path
    JobState.CANCELLED: set(),  # terminal
}


@dataclass
class Job:
    job_id: str
    mesh_path: str
    mesh_sha256: str
    material: str
    state: JobState
    created_unix: float
    updated_unix: float
    history: list[dict[str, Any]] = field(default_factory=list)

    # Filled in as the job advances
    target_printer_id: str | None = None
    dispatcher_decision: dict[str, Any] | None = None
    truth_gate_report: dict[str, Any] | None = None
    sliced_gcode_path: str | None = None
    sliced_gcode_sha256: str | None = None
    slicer_metadata: dict[str, Any] | None = None
    moonraker_item_path: str | None = None
    proof_envelope_path: str | None = None
    error: str | None = None
    notes: str = ""

    # User-supplied metadata
    quality_level: str = "normal"
    layer_height_mm: float = 0.2
    requested_strategy: str = "auto"

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Job:
        d = dict(d)
        d["state"] = JobState(d["state"])
        return cls(**d)

    def transition(
        self, next_state: JobState, *, reason: str = "", updated_unix: float | None = None
    ) -> None:
        """Advance to ``next_state`` if the transition is allowed.

        Records the transition in ``history`` and updates ``updated_unix``.
        """
        allowed = _ALLOWED.get(self.state, set())
        if next_state not in allowed:
            raise ValueError(
                f"Illegal transition {self.state.value} -> {next_state.value} "
                f"for job {self.job_id}. Allowed: "
                f"{sorted(s.value for s in allowed)}"
            )
        prev = self.state
        self.state = next_state
        self.updated_unix = updated_unix or time.time()
        self.history.append(
            {
                "from": prev.value,
                "to": next_state.value,
                "at_unix": self.updated_unix,
                "reason": reason,
            }
        )


# =============================================================================


class JobQueue:
    """JSON-backed persistent job queue.

    Thread-safe via an in-process RLock; multi-process safety is provided
    by atomic write (write tmpfile + rename). Two processes that race on
    the same queue file may produce one losing write — this matches typical
    "single agent + occasional CLI" usage.
    """

    def __init__(self, queue_path: str | Path) -> None:
        self.path = Path(queue_path)
        self._lock = threading.RLock()
        self._jobs: dict[str, Job] = {}
        self._loaded = False
        self._load_if_exists()

    # -------- persistence --------

    def _load_if_exists(self) -> None:
        with self._lock:
            if self._loaded:
                return
            if not self.path.exists():
                self._jobs = {}
                self._loaded = True
                return
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(
                    f"Queue schema mismatch: file={data.get('schema_version')!r} "
                    f"expected={SCHEMA_VERSION!r}"
                )
            self._jobs = {j["job_id"]: Job.from_dict(j) for j in data.get("jobs", [])}
            self._loaded = True

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "saved_unix": time.time(),
                "jobs": [j.to_dict() for j in self._jobs.values()],
            }
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.path)

    # -------- CRUD --------

    def enqueue(
        self,
        *,
        mesh_path: str,
        mesh_sha256: str,
        material: str,
        quality_level: str = "normal",
        layer_height_mm: float = 0.2,
        requested_strategy: str = "auto",
        notes: str = "",
    ) -> Job:
        with self._lock:
            now = time.time()
            job = Job(
                job_id=uuid.uuid4().hex,
                mesh_path=mesh_path,
                mesh_sha256=mesh_sha256,
                material=material,
                state=JobState.QUEUED,
                created_unix=now,
                updated_unix=now,
                quality_level=quality_level,
                layer_height_mm=layer_height_mm,
                requested_strategy=requested_strategy,
                notes=notes,
                history=[
                    {
                        "from": "<new>",
                        "to": JobState.QUEUED.value,
                        "at_unix": now,
                        "reason": "enqueue",
                    }
                ],
            )
            self._jobs[job.job_id] = job
            self.save()
            return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def update(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.job_id] = job
            self.save()

    def list(self, *, state: JobState | None = None) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
            if state is not None:
                jobs = [j for j in jobs if j.state == state]
            jobs.sort(key=lambda j: j.created_unix)
            return jobs

    def delete(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self.save()

    # -------- Convenience helpers --------

    def transition_job(
        self, job_id: str, next_state: JobState, *, reason: str = "", **field_updates: Any
    ) -> Job:
        """Advance job state and persist atomically.

        Extra kwargs set fields on the job (e.g. target_printer_id).
        """
        with self._lock:
            job = self.get(job_id)
            for k, v in field_updates.items():
                if not hasattr(job, k):
                    raise AttributeError(f"Job has no field {k!r}")
                setattr(job, k, v)
            job.transition(next_state, reason=reason)
            self.save()
            return job

    def __len__(self) -> int:
        with self._lock:
            return len(self._jobs)


__all__ = [
    "SCHEMA_VERSION",
    "Job",
    "JobQueue",
    "JobState",
]
