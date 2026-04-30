"""Obico bridge — closed-loop AI failure detection.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §35 (Obico Failure Detection)

Obico (formerly The Spaghetti Detective) provides ML-based print failure
detection. Self-hosted via Docker, free for personal use, no telemetry.
This client polls Obico for the current "spaghetti score" of an active
print and raises actionable alerts.

API surface (Obico self-hosted):
    GET  /api/v1/printers/         list configured printers
    GET  /api/v1/printers/{id}/    detailed printer state, including
                                    `current_print` with `prediction`
                                    (failure probability 0..1)
    POST /api/v1/printers/{id}/cancel_print/

The agent treats prediction > FAILURE_THRESHOLD as a strong signal and
either pauses or notifies depending on user policy.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import logging
import os
import socket
from dataclasses import dataclass, field
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


log = logging.getLogger(__name__)


DEFAULT_FAILURE_THRESHOLD = 0.45  # Obico's recommended action threshold
DEFAULT_HEADS_UP_THRESHOLD = 0.20  # warn but don't act


class ObicoAction(str, enum.Enum):
    OK = "ok"
    HEADS_UP = "heads_up"
    PAUSE = "pause"
    CANCEL = "cancel"


@dataclass
class ObicoStatus:
    printer_id: str
    is_printing: bool
    failure_probability: float
    detective_p: float | None = None  # raw "spaghetti P" score
    print_filename: str | None = None
    elapsed_seconds: int | None = None
    recommended_action: ObicoAction = ObicoAction.OK

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["recommended_action"] = self.recommended_action.value
        return d


@dataclass
class ObicoClient:
    base_url: str
    api_key: str | None = None
    timeout_s: float = 6.0
    failure_threshold: float = DEFAULT_FAILURE_THRESHOLD
    heads_up_threshold: float = DEFAULT_HEADS_UP_THRESHOLD

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        token = self.api_key or os.environ.get("OBICO_API_KEY", "")
        if token:
            h["Authorization"] = f"Token {token}"
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        h = dict(self._headers())
        if data is not None:
            h["Content-Type"] = "application/json"
        req = urlrequest.Request(url, data=data, method=method, headers=h)
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Obico HTTP {exc.code} on {path}")
        except (URLError, socket.timeout) as exc:
            raise RuntimeError(f"Obico network error: {exc}")

    def reachable(self) -> bool:
        try:
            self._request("GET", "/api/v1/printers/")
            return True
        except Exception:  # noqa: BLE001
            return False

    def list_printers(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/api/v1/printers/")
        return list(data) if isinstance(data, list) else data.get("results", [])

    def status(self, printer_id: str) -> ObicoStatus:
        data = self._request("GET", f"/api/v1/printers/{printer_id}/")
        current = data.get("current_print") or {}
        prediction = current.get("prediction") or {}
        prob = float(prediction.get("normalized_p", prediction.get("p", 0.0) or 0.0))
        action = ObicoAction.OK
        if prob >= self.failure_threshold:
            action = ObicoAction.PAUSE
        elif prob >= self.heads_up_threshold:
            action = ObicoAction.HEADS_UP
        return ObicoStatus(
            printer_id=str(printer_id),
            is_printing=bool(current.get("started_at")),
            failure_probability=prob,
            detective_p=prediction.get("p"),
            print_filename=(current.get("filename") or current.get("name")),
            elapsed_seconds=current.get("elapsed_seconds"),
            recommended_action=action,
        )

    def cancel_print(self, printer_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/printers/{printer_id}/cancel_print/")


__all__ = [
    "DEFAULT_FAILURE_THRESHOLD",
    "DEFAULT_HEADS_UP_THRESHOLD",
    "ObicoAction",
    "ObicoClient",
    "ObicoStatus",
]
