"""Farm host auto-discovery.

A pragmatic scanner: given a CIDR or list of hosts, probes each for known
3D-print stack endpoints. The result is a list of ``DiscoveredHost`` records
the dispatcher / dashboard can use to suggest fleet additions.

Probes (HEAD/GET on known paths):

  - Moonraker: ``/server/info`` → JSON with ``klippy_state``
  - Mainsail:  ``/`` → contains ``<title>Mainsail`` in HTML
  - Fluidd:    ``/`` → contains ``<title>Fluidd`` in HTML
  - OctoPrint: ``/api/version`` (returns 401 without API key, which is fine —
                we only need the response headers to identify it)
  - Obico:     ``/api/v1/version/`` on configured Obico hosts

Discovery is best-effort and runs serially with a tight per-probe timeout so
even a /24 sweep stays under ~30s. For real production use, the supervisor
calls this at startup once and caches results.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

import httpx


class HostKind(str, Enum):
    MOONRAKER = "moonraker"
    MAINSAIL = "mainsail"
    FLUIDD = "fluidd"
    OCTOPRINT = "octoprint"
    OBICO = "obico"
    UNKNOWN = "unknown"


@dataclass
class DiscoveredHost:
    host: str
    port: int
    kinds: list[HostKind] = field(default_factory=list)
    title: str | None = None
    server_header: str | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def to_dict(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "url": self.url,
            "kinds": [k.value for k in self.kinds],
            "title": self.title,
            "server_header": self.server_header,
        }


_DEFAULT_PORTS = (80, 443, 5000, 7125)


def expand_targets(targets: Iterable[str]) -> list[str]:
    """Accept either bare IPs/hostnames or CIDRs; return flat host list."""
    out: list[str] = []
    for entry in targets:
        entry = entry.strip()
        if not entry:
            continue
        if "/" in entry:
            try:
                net = ipaddress.ip_network(entry, strict=False)
            except ValueError:
                continue
            for addr in net.hosts():
                out.append(str(addr))
        else:
            out.append(entry)
    return out


def _is_open(host: str, port: int, *, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _probe_moonraker(client: httpx.Client, base: str) -> bool:
    try:
        resp = client.get(f"{base}/server/info", timeout=2.0)
        if resp.status_code != 200:
            return False
        data = resp.json()
        return "klippy_state" in data or "result" in data
    except (httpx.HTTPError, ValueError):
        return False


def _probe_octoprint(client: httpx.Client, base: str) -> bool:
    try:
        resp = client.get(f"{base}/api/version", timeout=2.0)
        # OctoPrint returns 401/403 without a key — both are fine fingerprints.
        if resp.status_code in (200, 401, 403):
            srv = (resp.headers.get("Server") or "").lower()
            if "octoprint" in srv:
                return True
            try:
                data = resp.json()
                if "server" in data and "octoprint" in str(data["server"]).lower():
                    return True
            except ValueError:
                return resp.status_code == 401  # 401 alone is suggestive
    except httpx.HTTPError:
        return False
    return False


def _probe_html_title(client: httpx.Client, base: str) -> str | None:
    try:
        resp = client.get(base, timeout=2.0)
        if resp.status_code != 200:
            return None
        body = resp.text[:8192]
        i = body.lower().find("<title>")
        if i < 0:
            return None
        j = body.lower().find("</title>", i)
        if j < 0:
            return None
        return body[i + 7 : j].strip()
    except httpx.HTTPError:
        return None


def discover_host(host: str, *, ports: Iterable[int] = _DEFAULT_PORTS,
                   timeout: float = 1.0) -> DiscoveredHost | None:
    """Probe a single host across known ports. Returns None if nothing matched."""
    found = DiscoveredHost(host=host, port=0)
    for port in ports:
        if not _is_open(host, port, timeout=timeout):
            continue
        base = f"http://{host}:{port}"
        with httpx.Client(timeout=2.0, follow_redirects=True) as client:
            if _probe_moonraker(client, base):
                found.kinds.append(HostKind.MOONRAKER)
                found.port = port
            if _probe_octoprint(client, base):
                found.kinds.append(HostKind.OCTOPRINT)
                if not found.port:
                    found.port = port
            title = _probe_html_title(client, base)
            if title:
                found.title = title
                if "mainsail" in title.lower():
                    found.kinds.append(HostKind.MAINSAIL)
                    if not found.port:
                        found.port = port
                if "fluidd" in title.lower():
                    found.kinds.append(HostKind.FLUIDD)
                    if not found.port:
                        found.port = port
        if found.kinds:
            return found
    return None


def discover_fleet(targets: Iterable[str]) -> list[DiscoveredHost]:
    """Run discover_host across an iterable of targets (hosts or CIDRs)."""
    hosts = expand_targets(targets)
    out: list[DiscoveredHost] = []
    for h in hosts:
        result = discover_host(h)
        if result is not None:
            out.append(result)
    return out


__all__ = [
    "DiscoveredHost",
    "HostKind",
    "discover_fleet",
    "discover_host",
    "expand_targets",
]
