"""OctoPrint REST client.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §34 (OctoPrint Bridge)

For users running OctoPrint instead of (or alongside) Moonraker. Same
shape as MoonrakerClient — reachable, state, upload, start, cancel —
so the dispatcher and orchestrator can target either ecosystem
transparently.

OctoPrint API docs: https://docs.octoprint.org/en/master/api/
Auth: a long-lived API key in the X-Api-Key header.
"""
from __future__ import annotations

import json
import logging
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


log = logging.getLogger(__name__)


@dataclass
class OctoPrintClient:
    base_url: str
    api_key: str | None = None
    timeout_s: float = 6.0

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-Api-Key"] = self.api_key
        elif (env := os.environ.get("OCTOPRINT_API_KEY")):
            h["X-Api-Key"] = env
        return h

    def _request(self, method: str, path: str,
                  *, body: dict[str, Any] | bytes | None = None,
                  headers: dict[str, str] | None = None,
                  ) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        h = dict(self._headers())
        if headers:
            h.update(headers)
        data: bytes | None = None
        if body is not None:
            if isinstance(body, (bytes, bytearray)):
                data = bytes(body)
            else:
                data = json.dumps(body).encode("utf-8")
        req = urlrequest.Request(url, data=data, method=method, headers=h)
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                ct = resp.headers.get("Content-Type", "")
                if "json" in ct:
                    return json.loads(raw.decode("utf-8"))
                return {"raw": raw.decode("utf-8", errors="replace")}
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            raise RuntimeError(f"OctoPrint HTTP {exc.code} on {path}: {detail[:200]}")
        except (URLError, socket.timeout) as exc:
            raise RuntimeError(f"OctoPrint network error: {exc}")

    # ---- High-level API -------------------------------------------------

    def reachable(self) -> bool:
        try:
            self._request("GET", "/api/version")
            return True
        except Exception:  # noqa: BLE001
            return False

    def version(self) -> dict[str, Any]:
        return self._request("GET", "/api/version")

    def printer_state(self) -> dict[str, Any]:
        try:
            data = self._request("GET", "/api/printer")
            flags = data.get("state", {}).get("flags", {})
            text = data.get("state", {}).get("text", "")
            return {
                "reachable": True,
                "printer_state_text": text,
                "is_printing": bool(flags.get("printing")),
                "is_paused": bool(flags.get("paused")),
                "is_operational": bool(flags.get("operational")),
                "is_error": bool(flags.get("error")),
                "raw": data,
            }
        except Exception as exc:  # noqa: BLE001
            return {"reachable": False, "error": str(exc)}

    def upload_gcode(self, gcode_path: str | Path,
                       *, location: str = "local") -> str:
        """Upload a g-code file via multipart form to /api/files/{location}.

        Returns the file's path on the OctoPrint server.
        """
        gcode_path = Path(gcode_path)
        if not gcode_path.exists():
            raise FileNotFoundError(gcode_path)
        boundary = "-----hermes3d-" + os.urandom(8).hex()
        crlf = b"\r\n"
        body = b""
        body += f"--{boundary}{crlf.decode()}".encode()
        body += (f'Content-Disposition: form-data; name="file"; '
                  f'filename="{gcode_path.name}"\r\n').encode()
        body += b"Content-Type: application/octet-stream\r\n\r\n"
        body += gcode_path.read_bytes()
        body += crlf
        body += f"--{boundary}--{crlf.decode()}".encode()
        h = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        resp = self._request("POST", f"/api/files/{location}",
                              body=body, headers=h)
        return resp.get("files", {}).get(location, {}).get("path",
                                                              gcode_path.name)

    def start_print(self, gcode_relpath: str, *, location: str = "local",
                     ) -> dict[str, Any]:
        return self._request("POST", f"/api/files/{location}/{gcode_relpath}",
                               body={"command": "select", "print": True})

    def cancel_print(self) -> dict[str, Any]:
        return self._request("POST", "/api/job",
                               body={"command": "cancel"})

    def pause_print(self) -> dict[str, Any]:
        return self._request("POST", "/api/job",
                               body={"command": "pause", "action": "pause"})

    def resume_print(self) -> dict[str, Any]:
        return self._request("POST", "/api/job",
                               body={"command": "pause", "action": "resume"})


__all__ = ["OctoPrintClient"]
