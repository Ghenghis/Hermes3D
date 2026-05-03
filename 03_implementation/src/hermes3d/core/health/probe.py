"""Service-health port probe — stdlib socket only.

Why stdlib? `port-monitor` (rakaarwaky/port-monitor on GitHub) is a C++/Qt6
desktop GUI application, **not** a Python library. We can't import it.
Instead we use ``socket.connect_ex`` for fast TCP-reachability probing
across a known list of Hermes3D-relevant services.

The probe answers a single question: *is the service accepting TCP
connections right now?* It deliberately does **not** perform any HTTP
request, because:

* an HTTP probe forces us to handle each service's auth scheme;
* the React UI just needs a green/red signal at a glance;
* richer per-service introspection is the job of the per-tab adapters
  (e.g. Moonraker fleet probe, provider-health gateway).

Per-printer Moonraker entries are derived from
``03_implementation/config/printers.toml`` plus the optional gitignored
``printers.user.toml`` override file. If neither file exists we silently
return ``()`` — the API stays useful even on a fresh checkout.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import tomllib
except ImportError:  # Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]


__all__ = [
    "KNOWN_SERVICES",
    "ProbeResult",
    "ServiceSpec",
    "Status",
    "moonraker_specs_from_config",
    "probe_all",
    "probe_one",
]


class Status(str, Enum):
    """Discrete status pip values understood by the React StatusPill."""

    ONLINE = "online"
    OFFLINE = "offline"
    UNREACHABLE = "unreachable"
    AUTH_REQUIRED = "auth-required"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ServiceSpec:
    """Static description of one probe target.

    ``port == 0`` is special-cased to mean "stdio service" (e.g. an MCP
    server speaking JSON-RPC over stdin/stdout) — we can't TCP-probe it,
    so we report :class:`Status.UNKNOWN` and let the caller decide.
    """

    name: str
    host: str
    port: int
    category: str  # "mcp" | "llm" | "modeling" | "printer" | "api" | "tunnel"
    enabled: bool = True
    http_health_path: str | None = None  # informational; not yet probed


@dataclass
class ProbeResult:
    spec: ServiceSpec
    status: Status
    detail: str
    latency_ms: float
    probed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# -----------------------------------------------------------------------------
# Default service catalogue
# -----------------------------------------------------------------------------

KNOWN_SERVICES: tuple[ServiceSpec, ...] = (
    # `port=0` means stdio — special-cased in probe_one.
    ServiceSpec("HermesProof MCP", "127.0.0.1", 0, "mcp", enabled=False),
    ServiceSpec("LM Studio", "127.0.0.1", 1234, "llm", http_health_path="/v1/models"),
    ServiceSpec("Ollama", "127.0.0.1", 11434, "llm", http_health_path="/api/tags"),
    # Optional secondary node (AMD box). Disabled unless explicitly enabled.
    ServiceSpec("Hipfire (AMD)", "127.0.0.1", 11435, "llm", enabled=False),
    ServiceSpec("Blender MCP", "127.0.0.1", 9876, "modeling"),
    ServiceSpec("ComfyUI", "127.0.0.1", 8188, "modeling"),
    ServiceSpec("FastAPI server", "127.0.0.1", 8000, "api"),
    ServiceSpec("Gradio launcher", "127.0.0.1", 7860, "api"),
)


# -----------------------------------------------------------------------------
# Probing
# -----------------------------------------------------------------------------


def probe_one(spec: ServiceSpec, timeout_s: float = 2.0) -> ProbeResult:
    """Probe a single service via TCP ``connect_ex``.

    The default 2 s timeout matches the Service Health spec; callers can
    override it for faster batch probes (e.g. dashboards on a 30 s loop)
    or longer timeouts for lossy WAN links.
    """
    if not spec.enabled:
        return ProbeResult(spec, Status.DISABLED, "service disabled by config", 0.0)
    if spec.port == 0:
        return ProbeResult(
            spec,
            Status.UNKNOWN,
            "stdio service; probe via MCP handshake separately",
            0.0,
        )

    start = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            rc = s.connect_ex((spec.host, spec.port))
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if rc == 0:
            return ProbeResult(
                spec,
                Status.ONLINE,
                f"TCP {spec.host}:{spec.port} accepted",
                elapsed_ms,
            )
        return ProbeResult(
            spec,
            Status.OFFLINE,
            f"TCP {spec.host}:{spec.port} refused (errno={rc})",
            elapsed_ms,
        )
    except socket.gaierror as exc:
        return ProbeResult(spec, Status.UNREACHABLE, f"DNS/host error: {exc}", 0.0)
    except OSError as exc:
        return ProbeResult(spec, Status.UNREACHABLE, f"socket error: {exc}", 0.0)


def probe_all(extra: tuple[ServiceSpec, ...] = ()) -> list[ProbeResult]:
    """Probe :data:`KNOWN_SERVICES` plus any caller-supplied extras.

    The caller typically supplies per-printer Moonraker specs derived
    from :func:`moonraker_specs_from_config`. The order is preserved:
    KNOWN_SERVICES first, extras last.
    """
    return [probe_one(s) for s in (*KNOWN_SERVICES, *extra)]


# -----------------------------------------------------------------------------
# Per-printer Moonraker spec generation
# -----------------------------------------------------------------------------


def _parse_moonraker_url(url: str) -> tuple[str, int]:
    """Return ``(host, port)`` from a Moonraker URL.

    Falls back to the Moonraker default port 7125 when none is specified.
    """
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = parsed.hostname or url
    port = parsed.port or 7125
    return host, port


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def moonraker_specs_from_config(
    *,
    stock: Path | None = None,
    user: Path | None = None,
) -> tuple[ServiceSpec, ...]:
    """Build Moonraker :class:`ServiceSpec` entries from printer config.

    Reads the stock manifest (``config/printers.toml``) and an optional
    per-machine override (``config/printers.user.toml``). User entries
    override stock entries by ``printer_id``. If neither file exists we
    return ``()`` — a fresh checkout with no printers configured is fine.
    """
    repo_config = Path(__file__).resolve().parent.parent.parent.parent.parent / "config"
    stock_path = stock if stock is not None else repo_config / "printers.toml"
    user_path = user if user is not None else repo_config / "printers.user.toml"

    merged: dict[str, dict[str, Any]] = {}
    for path in (stock_path, user_path):
        data = _load_toml(path)
        printers = data.get("printers", {}) if isinstance(data, dict) else {}
        if not isinstance(printers, dict):
            continue
        for printer_id, fields in printers.items():
            if not isinstance(fields, dict):
                continue
            merged.setdefault(printer_id, {}).update(fields)

    specs: list[ServiceSpec] = []
    for printer_id, fields in merged.items():
        url = fields.get("moonraker_url")
        if not isinstance(url, str) or not url:
            continue
        host, port = _parse_moonraker_url(url)
        specs.append(
            ServiceSpec(
                name=f"Moonraker — {printer_id}",
                host=host,
                port=port,
                category="printer",
                enabled=True,
            )
        )
    return tuple(specs)
