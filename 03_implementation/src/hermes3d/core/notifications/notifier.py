"""Notification dispatch — Discord, Slack, generic webhook.

Status: runnable
Contract: 00-CONTRACT/MASTER_CONTRACT.md §13 (Notifications)

Sends print-event notifications to one or more configured channels.
Channels are loaded from environment variables so secrets never enter the
repository:

    HERMES3D_DISCORD_WEBHOOK   -> Discord channel webhook URL
    HERMES3D_SLACK_WEBHOOK     -> Slack incoming webhook URL
    HERMES3D_GENERIC_WEBHOOK   -> POST raw JSON to this URL

Each notification is dispatched best-effort — failures are logged but do
not raise. Crucial: the calling pipeline must never wedge because a Slack
outage prevented a "print started" message from sending.
"""
from __future__ import annotations

import dataclasses
import enum
import json
import logging
import os
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


log = logging.getLogger(__name__)


class NotificationLevel(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class NotificationEvent:
    """A printer/job event worth notifying on."""

    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    printer_id: str | None = None
    job_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NotificationResult:
    channel: str
    sent: bool
    error: str | None = None


# =============================================================================


def _post_json(url: str, payload: dict[str, Any], *, timeout_s: float = 5.0,
               headers: dict[str, str] | None = None) -> tuple[bool, str | None]:
    """POST JSON to a webhook. Returns (sent, error_message)."""
    body = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urlrequest.Request(url, data=body, headers=h, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout_s) as resp:
            if 200 <= resp.status < 300:
                return True, None
            return False, f"HTTP {resp.status}"
    except HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.reason}"
    except (URLError, socket.timeout) as exc:
        return False, f"net: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"unexpected: {exc}"


# -- Discord -----------------------------------------------------------------

_DISCORD_COLOR = {
    NotificationLevel.INFO: 0x3498DB,     # blue
    NotificationLevel.SUCCESS: 0x2ECC71,  # green
    NotificationLevel.WARNING: 0xF39C12,  # orange
    NotificationLevel.ERROR: 0xE74C3C,    # red
}


def discord_payload(event: NotificationEvent) -> dict[str, Any]:
    fields: list[dict[str, str]] = []
    if event.printer_id:
        fields.append({"name": "Printer", "value": event.printer_id, "inline": True})
    if event.job_id:
        fields.append({"name": "Job", "value": event.job_id[:12], "inline": True})
    for k, v in event.extra.items():
        fields.append({"name": str(k), "value": str(v)[:200], "inline": True})
    return {
        "embeds": [{
            "title": event.title[:256],
            "description": event.message[:4000],
            "color": _DISCORD_COLOR[event.level],
            "fields": fields[:25],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "footer": {"text": "Hermes3D-OS Lite"},
        }],
    }


def send_discord(url: str, event: NotificationEvent, *,
                 timeout_s: float = 5.0) -> NotificationResult:
    sent, err = _post_json(url, discord_payload(event), timeout_s=timeout_s)
    return NotificationResult(channel="discord", sent=sent, error=err)


# -- Slack -------------------------------------------------------------------

_SLACK_COLOR = {
    NotificationLevel.INFO: "#3498DB",
    NotificationLevel.SUCCESS: "#2ECC71",
    NotificationLevel.WARNING: "#F39C12",
    NotificationLevel.ERROR: "#E74C3C",
}


def slack_payload(event: NotificationEvent) -> dict[str, Any]:
    fields: list[dict[str, str | bool]] = []
    if event.printer_id:
        fields.append({"title": "Printer", "value": event.printer_id, "short": True})
    if event.job_id:
        fields.append({"title": "Job", "value": event.job_id[:12], "short": True})
    for k, v in event.extra.items():
        fields.append({"title": str(k), "value": str(v)[:200], "short": True})
    return {
        "attachments": [{
            "color": _SLACK_COLOR[event.level],
            "title": event.title[:256],
            "text": event.message[:4000],
            "fields": fields[:20],
            "footer": "Hermes3D-OS Lite",
            "ts": int(time.time()),
        }],
    }


def send_slack(url: str, event: NotificationEvent, *,
               timeout_s: float = 5.0) -> NotificationResult:
    sent, err = _post_json(url, slack_payload(event), timeout_s=timeout_s)
    return NotificationResult(channel="slack", sent=sent, error=err)


# -- Generic webhook ---------------------------------------------------------


def send_generic(url: str, event: NotificationEvent, *,
                 timeout_s: float = 5.0) -> NotificationResult:
    payload = {
        "title": event.title,
        "message": event.message,
        "level": event.level.value,
        "printer_id": event.printer_id,
        "job_id": event.job_id,
        "extra": event.extra,
        "timestamp_unix": time.time(),
        "source": "hermes3d-os-lite",
    }
    sent, err = _post_json(url, payload, timeout_s=timeout_s)
    return NotificationResult(channel="generic", sent=sent, error=err)


# =============================================================================


class Notifier:
    """Dispatches an event to every channel configured via env vars."""

    def __init__(self, *, timeout_s: float = 5.0,
                 discord_url: str | None = None,
                 slack_url: str | None = None,
                 generic_url: str | None = None) -> None:
        self.timeout_s = timeout_s
        self.discord_url = discord_url or os.environ.get("HERMES3D_DISCORD_WEBHOOK")
        self.slack_url = slack_url or os.environ.get("HERMES3D_SLACK_WEBHOOK")
        self.generic_url = generic_url or os.environ.get("HERMES3D_GENERIC_WEBHOOK")

    @property
    def configured_channels(self) -> tuple[str, ...]:
        out: list[str] = []
        if self.discord_url:
            out.append("discord")
        if self.slack_url:
            out.append("slack")
        if self.generic_url:
            out.append("generic")
        return tuple(out)

    def notify(self, event: NotificationEvent) -> list[NotificationResult]:
        """Best-effort send to every configured channel.

        Always returns; never raises. Each failure is logged.
        """
        results: list[NotificationResult] = []
        if self.discord_url:
            r = send_discord(self.discord_url, event, timeout_s=self.timeout_s)
            results.append(r)
            if not r.sent:
                log.warning("Discord notification failed: %s", r.error)
        if self.slack_url:
            r = send_slack(self.slack_url, event, timeout_s=self.timeout_s)
            results.append(r)
            if not r.sent:
                log.warning("Slack notification failed: %s", r.error)
        if self.generic_url:
            r = send_generic(self.generic_url, event, timeout_s=self.timeout_s)
            results.append(r)
            if not r.sent:
                log.warning("Generic webhook failed: %s", r.error)
        return results


# Convenience presets ---------------------------------------------------------


def event_print_started(printer_id: str, job_id: str, filename: str) -> NotificationEvent:
    return NotificationEvent(
        title="🖨️ Print started",
        message=f"`{filename}` started on `{printer_id}`",
        level=NotificationLevel.INFO,
        printer_id=printer_id,
        job_id=job_id,
        extra={"filename": filename},
    )


def event_print_succeeded(printer_id: str, job_id: str, duration_min: float) -> NotificationEvent:
    return NotificationEvent(
        title="✅ Print finished",
        message=f"Job completed on `{printer_id}` in {duration_min:.1f} min",
        level=NotificationLevel.SUCCESS,
        printer_id=printer_id,
        job_id=job_id,
        extra={"duration_min": f"{duration_min:.1f}"},
    )


def event_print_failed(printer_id: str, job_id: str, error: str) -> NotificationEvent:
    return NotificationEvent(
        title="❌ Print failed",
        message=f"Job failed on `{printer_id}`: {error}",
        level=NotificationLevel.ERROR,
        printer_id=printer_id,
        job_id=job_id,
        extra={"error": error[:200]},
    )


def event_truth_gate_failed(printer_id: str, job_id: str, reason: str) -> NotificationEvent:
    return NotificationEvent(
        title="⚠️ Truth Gate rejected",
        message=f"Mesh did not pass Truth Gate for `{printer_id}`: {reason}",
        level=NotificationLevel.WARNING,
        printer_id=printer_id,
        job_id=job_id,
        extra={"reason": reason[:200]},
    )


__all__ = [
    "NotificationEvent",
    "NotificationLevel",
    "NotificationResult",
    "Notifier",
    "discord_payload",
    "event_print_failed",
    "event_print_started",
    "event_print_succeeded",
    "event_truth_gate_failed",
    "send_discord",
    "send_generic",
    "send_slack",
    "slack_payload",
]
