"""Risk-aware print scheduler + camera utilities.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §14 (Scheduling & Cameras)

Includes:
  - schedule_window():   policy-driven "should we start this print now?"
  - estimated_completion(): compute when a print will finish given duration
  - SchedulerPolicy:     user-tunable rules (quiet hours, max duration, etc.)
  - CameraSnapshot:      pull a still image from a Moonraker-attached webcam

The scheduler is a pure function — no side effects. Callers (the orchestrator)
consume its decision and either start the print or queue it for later.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

# =============================================================================
# Scheduler
# =============================================================================


@dataclass(frozen=True)
class SchedulerPolicy:
    """User-tunable scheduling rules.

    All clock values use the local timezone of the host running this module.
    Times are integers 0-23.
    """

    quiet_hours_start: int = 23  # don't START prints after this hour
    quiet_hours_end: int = 6  # ...until this hour the next morning
    max_print_duration_minutes: int = 720  # 12h default ceiling
    max_finish_after_minutes: int = 1440  # ETA can't be > 24h from now
    allow_quiet_finish: bool = True
    # If True, a print started at 5pm that ends at 1am is OK (it just
    # crosses quiet hours). Only the START time is constrained.

    def __post_init__(self) -> None:
        for v in (self.quiet_hours_start, self.quiet_hours_end):
            if not 0 <= v <= 23:
                raise ValueError(f"quiet hour must be 0-23: {v}")


@dataclass(frozen=True)
class ScheduleDecision:
    allowed: bool
    reasons: tuple[str, ...]
    estimated_finish_local: str  # ISO8601 local time
    suggested_start_local: str | None = None  # if not allowed, when to retry


def _is_in_quiet_hours(hour: int, start: int, end: int) -> bool:
    """Quiet hours wrap midnight: e.g. 23..6 means 23,0,1,2,3,4,5."""
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def schedule_window(
    *, duration_minutes: float, policy: SchedulerPolicy, now: _dt.datetime | None = None
) -> ScheduleDecision:
    """Decide whether NOW is a valid start time for a print of given duration.

    Args:
        duration_minutes: g-code-estimated duration.
        policy: rules to apply.
        now: override (used by tests). Defaults to current local time.
    """
    now = now or _dt.datetime.now()
    finish = now + _dt.timedelta(minutes=duration_minutes)

    reasons: list[str] = []
    suggested: _dt.datetime | None = None

    # Rule 1: duration cap
    if duration_minutes > policy.max_print_duration_minutes:
        hours = duration_minutes / 60.0
        cap = policy.max_print_duration_minutes / 60.0
        reasons.append(f"duration {hours:.1f}h exceeds policy cap {cap:.1f}h")

    # Rule 2: ETA cap
    eta_delta_min = duration_minutes
    if eta_delta_min > policy.max_finish_after_minutes:
        reasons.append(
            f"ETA {eta_delta_min / 60.0:.1f}h exceeds policy cap "
            f"{policy.max_finish_after_minutes / 60.0:.1f}h"
        )

    # Rule 3: quiet hours START check
    if _is_in_quiet_hours(now.hour, policy.quiet_hours_start, policy.quiet_hours_end):
        reasons.append(
            f"current time {now.strftime('%H:%M')} is inside quiet hours "
            f"({policy.quiet_hours_start:02d}:00-{policy.quiet_hours_end:02d}:00)"
        )
        # Suggest tomorrow at quiet_hours_end
        suggest_day = now.date()
        if now.hour >= policy.quiet_hours_start:
            suggest_day = suggest_day + _dt.timedelta(days=1)
        suggested = _dt.datetime.combine(
            suggest_day,
            _dt.time(hour=policy.quiet_hours_end, minute=0),
        )

    # Rule 4: finish-time check (only if allow_quiet_finish=False)
    if not policy.allow_quiet_finish:
        if _is_in_quiet_hours(finish.hour, policy.quiet_hours_start, policy.quiet_hours_end):
            reasons.append(f"finish time {finish.strftime('%H:%M')} is inside quiet hours")

    return ScheduleDecision(
        allowed=not reasons,
        reasons=tuple(reasons),
        estimated_finish_local=finish.strftime("%Y-%m-%dT%H:%M:%S"),
        suggested_start_local=(suggested.strftime("%Y-%m-%dT%H:%M:%S") if suggested else None),
    )


def estimated_completion(duration_minutes: float, now: _dt.datetime | None = None) -> _dt.datetime:
    """Convenience: returns wall-clock ETA for a print of given duration."""
    now = now or _dt.datetime.now()
    return now + _dt.timedelta(minutes=duration_minutes)


# =============================================================================
# Camera helper (Moonraker / mjpg-streamer compatible)
# =============================================================================


@dataclass
class CameraSnapshot:
    """A pulled webcam frame."""

    printer_id: str
    image_bytes: bytes
    content_type: str
    saved_to: str | None = None


def fetch_camera_snapshot(
    *,
    moonraker_base_url: str,
    printer_id: str,
    stream_path: str = "/webcam/?action=snapshot",
    timeout_s: float = 8.0,
    save_to: str | Path | None = None,
) -> CameraSnapshot:
    """Pull a single still frame from a printer's webcam.

    The default ``stream_path`` matches mjpg-streamer / Crowsnest default
    routes used by Mainsail and Fluidd. For setups behind a Moonraker
    `cameras` config block, change to e.g. `/server/webcams/get_image`.
    """
    url = moonraker_base_url.rstrip("/") + stream_path
    req = urlrequest.Request(url, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=timeout_s) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            image = resp.read()
    except (TimeoutError, HTTPError, URLError) as exc:
        raise RuntimeError(f"Camera fetch failed for {printer_id}: {exc}") from exc

    saved_path: str | None = None
    if save_to is not None:
        out = Path(save_to)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(image)
        saved_path = str(out.resolve())

    return CameraSnapshot(
        printer_id=printer_id,
        image_bytes=image,
        content_type=content_type,
        saved_to=saved_path,
    )


__all__ = [
    "CameraSnapshot",
    "ScheduleDecision",
    "SchedulerPolicy",
    "estimated_completion",
    "fetch_camera_snapshot",
    "schedule_window",
]
