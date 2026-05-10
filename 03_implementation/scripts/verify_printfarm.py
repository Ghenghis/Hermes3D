"""Read-only print-farm service verifier (H3D-CLAUDE-SOURCE-PRINTFARM).

Probes Moonraker / Klipper / Fluidd / Mainsail / OctoPrint / Printrun /
FDM Monster / KlipperScreen using ONLY HTTP GET with the Python stdlib
(urllib + json). It NEVER POSTs, NEVER uploads, NEVER issues G-code, and
NEVER touches the FLSUN S1 (192.168.0.12) which is a read-only camera per
lane policy.

Output: writes
  03_implementation/proof/PRINTFARM_VERIFY_2026-05-06.json

Each probe records: service, target, reachable (bool), version (str|null),
error (str|null), policy (str|null). Honest "unreachable" is correct;
fabrication is not.

Usage:
    python 03_implementation/scripts/verify_printfarm.py
"""

from __future__ import annotations

import json
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPL_ROOT = REPO_ROOT / "03_implementation"
PROOF_PATH = IMPL_ROOT / "proof" / "PRINTFARM_VERIFY_2026-05-06.json"

TIMEOUT_SECONDS = 2.0

# Lane-policy printer fleet (only reachable on local LAN; honest unreachable
# is the correct outcome when off-network).
PRINTERS: list[dict[str, Any]] = [
    {
        "name": "flsun_s1_camera",
        "ip": "192.168.0.12",
        "port": None,
        "service": "flsun_s1_camera",
        "policy": "camera-read-only-skipped",
    },
    {
        "name": "flsun_t1_a",
        "ip": "192.168.0.10",
        "port": 7125,
        "service": "moonraker",
        "policy": "read-only-moonraker-get-only",
    },
    {
        "name": "flsun_t1_b",
        "ip": "192.168.0.11",
        "port": 7125,
        "service": "moonraker",
        "policy": "read-only-moonraker-get-only",
    },
    {
        "name": "flsun_v400",
        "ip": "192.168.0.34",
        "port": 7125,
        "service": "moonraker",
        "policy": "read-only-moonraker-get-only",
    },
]

# Service classes that probe localhost-style endpoints. None of these ever
# POST or upload — all are HTTP GET against documented info endpoints.
LOCAL_SERVICES: list[dict[str, Any]] = [
    {
        "service": "fluidd",
        "endpoint": "http://127.0.0.1:80/",
        "version_path": None,
        "policy": "read-only-static-ui-probe",
    },
    {
        "service": "mainsail",
        "endpoint": "http://127.0.0.1:80/",
        "version_path": None,
        "policy": "read-only-static-ui-probe",
    },
    {
        "service": "octoprint",
        "endpoint": "http://127.0.0.1:5000/api/version",
        "version_path": ["server"],
        "policy": "read-only-version-endpoint",
    },
    {
        "service": "fdm_monster",
        "endpoint": "http://127.0.0.1:4000/api/settings",
        "version_path": None,
        "policy": "read-only-settings-probe",
    },
    {
        "service": "klipperscreen",
        "endpoint": None,  # KlipperScreen is a local TFT GUI — no HTTP API.
        "version_path": None,
        "policy": "no-network-tft-gui-runtime-only",
    },
    {
        "service": "printrun",
        "endpoint": None,  # Printrun is a USB serial CLI/GUI — no HTTP.
        "version_path": None,
        "policy": "no-network-usb-cli-runtime-only",
    },
]


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _http_get_json(
    url: str, timeout: float = TIMEOUT_SECONDS
) -> tuple[bool, Any | None, str | None]:
    """GET url with a strict timeout. Returns (ok, json_or_text, error_or_none)."""
    request = urllib.request.Request(
        url, method="GET", headers={"User-Agent": "hermes3d-source-printfarm-verify/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 — strict GET, http only.
            status = response.status
            raw = response.read()
            if status != 200:
                return False, None, f"http_{status}"
            text = raw.decode("utf-8", errors="replace")
            try:
                return True, json.loads(text), None
            except json.JSONDecodeError:
                return True, text, None
    except urllib.error.HTTPError as exc:
        return False, None, f"http_{exc.code}"
    except urllib.error.URLError as exc:
        return False, None, f"url_error:{exc.reason!s}"
    except (TimeoutError, socket.timeout):
        return False, None, "timeout"
    except OSError as exc:
        return False, None, f"os_error:{exc!s}"


def _extract_version(payload: Any, version_path: list[str] | None) -> str | None:
    if payload is None:
        return None
    if version_path is None:
        return None
    if isinstance(payload, dict):
        node: Any = payload
        for key in version_path:
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
        if isinstance(node, str):
            return node
    return None


def probe_moonraker(ip: str, port: int) -> dict[str, Any]:
    """Read-only GET /server/info on Moonraker."""
    url = f"http://{ip}:{port}/server/info"
    started = time.monotonic()
    ok, payload, err = _http_get_json(url)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    version: str | None = None
    if ok and isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, dict):
            mr = result.get("moonraker_version")
            if isinstance(mr, str):
                version = mr
    return {
        "url": url,
        "method": "GET",
        "reachable": bool(ok),
        "version": version,
        "error": err,
        "elapsed_ms": elapsed_ms,
    }


def probe_local_service(service: dict[str, Any]) -> dict[str, Any]:
    endpoint = service.get("endpoint")
    if not endpoint:
        # Service has no HTTP API (e.g. KlipperScreen TFT, Printrun USB CLI).
        # Detect runtime presence via PATH only — no network call.
        binary = None
        if service["service"] == "printrun":
            for name in ("pronterface", "pronterface.exe", "pronsole", "pronsole.exe"):
                found = shutil.which(name)
                if found:
                    binary = found
                    break
        return {
            "url": None,
            "method": None,
            "reachable": bool(binary),
            "version": None,
            "error": None if binary else "no_network_api_and_binary_not_on_path",
            "elapsed_ms": 0,
            "binary_on_path": binary,
        }

    started = time.monotonic()
    ok, payload, err = _http_get_json(endpoint)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    version = _extract_version(payload, service.get("version_path"))
    return {
        "url": endpoint,
        "method": "GET",
        "reachable": bool(ok),
        "version": version,
        "error": err,
        "elapsed_ms": elapsed_ms,
    }


def main() -> int:
    PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)

    printer_results: list[dict[str, Any]] = []
    for printer in PRINTERS:
        entry: dict[str, Any] = {
            "name": printer["name"],
            "ip": printer["ip"],
            "port": printer["port"],
            "service": printer["service"],
            "policy": printer["policy"],
        }
        if printer["policy"] == "camera-read-only-skipped":
            entry.update(
                {
                    "skipped": True,
                    "reachable": None,
                    "version": None,
                    "url": None,
                    "method": None,
                    "error": None,
                    "elapsed_ms": 0,
                    "note": "S1 camera — lane policy: never probe.",
                }
            )
        else:
            entry["skipped"] = False
            probe = probe_moonraker(printer["ip"], printer["port"])
            entry.update(probe)
        printer_results.append(entry)

    service_results: list[dict[str, Any]] = []
    for service in LOCAL_SERVICES:
        entry = {
            "service": service["service"],
            "policy": service["policy"],
        }
        probe = probe_local_service(service)
        entry.update(probe)
        service_results.append(entry)

    proof: dict[str, Any] = {
        "schema": "hermes3d://proof/printfarm_verify/v1",
        "lane": "H3D-CLAUDE-SOURCE-PRINTFARM",
        "generated_at": _now_iso(),
        "tool": "verify_printfarm.py",
        "policy": {
            "read_only": True,
            "no_post": True,
            "no_gcode_upload": True,
            "timeout_seconds": TIMEOUT_SECONDS,
            "s1_camera_skipped": True,
        },
        "printers": printer_results,
        "services": service_results,
        "summary": {
            "printers_total": len(printer_results),
            "printers_skipped": sum(1 for p in printer_results if p.get("skipped")),
            "printers_reachable": sum(1 for p in printer_results if p.get("reachable") is True),
            "printers_unreachable": sum(1 for p in printer_results if p.get("reachable") is False),
            "services_total": len(service_results),
            "services_reachable": sum(1 for s in service_results if s.get("reachable") is True),
            "services_unreachable": sum(1 for s in service_results if s.get("reachable") is False),
        },
    }

    PROOF_PATH.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {PROOF_PATH}")
    print(json.dumps(proof["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
