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
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def probe_one(
    spec: ServiceSpec,
    timeout_s: float = 2.0,
    http_check: bool = True,
) -> ProbeResult:
    """Probe a single service via TCP ``connect_ex`` plus optional HTTP readiness.

    The default 2 s timeout matches the Service Health spec; callers can
    override it for faster batch probes (e.g. dashboards on a 30 s loop)
    or longer timeouts for lossy WAN links.

    When ``http_check`` is True (the default) and the spec carries an
    ``http_health_path``, a follow-up HTTP GET validates the service is
    actually ready, not just accepting TCP connections. Codex audit on
    PR #42 (2026-05-03) flagged TCP-only probes as a false-positive risk:
    Moonraker can answer TCP while Klipper is in ``shutdown`` or ``error``
    state, leaving the printer unusable but reported "online". The HTTP
    layer reads ``/server/info`` for Moonraker (or ``/api/tags`` etc. for
    LLM endpoints) and downgrades to AUTH_REQUIRED / OFFLINE when the
    response disagrees with TCP-level reachability.
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
        if rc != 0:
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

    # TCP open. Optionally upgrade with HTTP readiness check.
    if http_check and spec.http_health_path:
        http_status = _http_readiness_check(spec, timeout_s)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if http_status is not None:
            status, detail = http_status
            return ProbeResult(spec, status, detail, elapsed_ms)

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return ProbeResult(
        spec,
        Status.ONLINE,
        f"TCP {spec.host}:{spec.port} accepted",
        elapsed_ms,
    )


def _http_readiness_check(spec: ServiceSpec, timeout_s: float) -> tuple[Status, str] | None:
    """HTTP-level readiness check for services with ``http_health_path`` set.

    Returns ``(Status, detail)`` if the HTTP layer adds information, or
    ``None`` to fall through to the default ONLINE verdict (when HTTP
    didn't disagree with TCP).

    Service-specific semantics:
      * Moonraker (``/server/info``): JSON with ``klippy_state``;
        only ``ready`` is fully ONLINE; ``startup`` is UNKNOWN; ``shutdown``,
        ``error``, or ``disconnected`` is OFFLINE.
      * LM Studio (``/v1/models``): 200 + JSON ``data`` array → ONLINE.
        401/403 → AUTH_REQUIRED. Other non-2xx → OFFLINE.
      * Ollama (``/api/tags``): 200 → ONLINE. Non-2xx → OFFLINE.
      * Generic: 2xx → ONLINE; 401/403 → AUTH_REQUIRED; other → OFFLINE.
    """
    import json
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    url = f"http://{spec.host}:{spec.port}{spec.http_health_path}"
    req = Request(url, method="GET", headers={"User-Agent": "hermes3d-health/1.0"})
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(8192)
            ctype = resp.headers.get("Content-Type", "")
    except HTTPError as exc:
        if exc.code in (401, 403):
            return (
                Status.AUTH_REQUIRED,
                f"HTTP {exc.code} {spec.http_health_path}",
            )
        return Status.OFFLINE, f"HTTP {exc.code} {spec.http_health_path}"
    except URLError as exc:
        return Status.OFFLINE, f"HTTP unreachable: {exc.reason}"
    except (TimeoutError, OSError) as exc:
        return Status.OFFLINE, f"HTTP error: {exc}"

    # Moonraker readiness check
    if spec.http_health_path == "/server/info":
        try:
            payload = json.loads(body.decode("utf-8", errors="replace"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Status.OFFLINE, f"non-JSON {spec.http_health_path} response"
        klippy_state = (
            payload.get("result", {}).get("klippy_state") or payload.get("klippy_state") or ""
        ).lower()
        if klippy_state == "ready":
            return Status.ONLINE, f"Klipper ready ({spec.http_health_path})"
        if klippy_state == "startup":
            return Status.UNKNOWN, f"Klipper starting ({klippy_state})"
        if klippy_state in ("shutdown", "error", "disconnected"):
            return Status.OFFLINE, f"Klipper {klippy_state}"
        return Status.UNKNOWN, f"Klipper state '{klippy_state}' (unrecognized)"

    # LM Studio readiness check
    if spec.http_health_path == "/v1/models":
        try:
            payload = json.loads(body.decode("utf-8", errors="replace"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Status.UNKNOWN, "non-JSON /v1/models response"
        if isinstance(payload.get("data"), list):
            return Status.ONLINE, f"{len(payload['data'])} models loaded"
        return Status.UNKNOWN, "no data array in /v1/models"

    # Ollama / generic
    if "json" in ctype.lower() or spec.http_health_path == "/api/tags":
        try:
            json.loads(body.decode("utf-8", errors="replace"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass  # generic 2xx still acceptable
    return None  # 2xx, no service-specific verdict to add — fall through to ONLINE


# W18-A18 — parallel probe execution.
#
# Audit (2026-05-11): operator reproduced /api/health/services hanging
# >60s on cold backend even after PR #244 added the honest-blocked
# banner for the 404 case. Real root cause: ``probe_all`` was a list
# comprehension running ``probe_one`` sequentially across every entry
# in :data:`KNOWN_SERVICES` plus every per-printer Moonraker spec from
# ``moonraker_specs_from_config()``. With 6 enabled known services +
# 12 printer specs and each ``probe_one`` carrying a 2 s TCP timeout
# (plus an optional 2 s HTTP follow-up), worst-case sequential latency
# is ``18 × 4 s = 72 s`` when nothing on the lab network is reachable.
# DNS resolution for ``*.local`` hostnames is not bounded by
# ``socket.settimeout()`` and can stall an entire probe up to the
# platform resolver default (~10 s on Windows).
#
# Fix: parallelize via ``ThreadPoolExecutor`` with an overall budget
# (``PROBE_ALL_DEADLINE_S``). Probes that don't finish before the
# budget expires are downgraded to :class:`Status.UNREACHABLE` —
# honest blocked, never faked online. The honest-empty path is
# preserved by ``api/routes/health_services.py`` when no probes are
# registered at all.
PROBE_ALL_DEADLINE_S: float = 3.5
PROBE_PER_TASK_TIMEOUT_S: float = 1.5


def _placeholder_result(spec: ServiceSpec, reason: str) -> ProbeResult:
    """Return a ``Status.UNREACHABLE`` ``ProbeResult`` for a probe that
    did not complete inside the parallel-probe budget. The honest-blocked
    contract requires we tell the UI *why* we are unreachable without
    inventing an "online" verdict.
    """
    return ProbeResult(spec, Status.UNREACHABLE, reason, 0.0)


def probe_all(extra: tuple[ServiceSpec, ...] = ()) -> list[ProbeResult]:
    """Probe :data:`KNOWN_SERVICES` plus any caller-supplied extras in parallel.

    The caller typically supplies per-printer Moonraker specs derived
    from :func:`moonraker_specs_from_config`. The output order matches
    the input order: KNOWN_SERVICES first, extras last — so the React
    Service Health table layout stays stable across reloads.

    Parallelization details:

    * One :class:`~concurrent.futures.ThreadPoolExecutor` thread per
      probe (capped at 32) — TCP + HTTP probes are I/O bound, so threads
      are the right unit; we are not CPU-constrained.
    * Overall budget ``PROBE_ALL_DEADLINE_S`` (4.5 s) applied via
      :func:`~concurrent.futures.as_completed`. Probes that don't
      finish in time return :class:`Status.UNREACHABLE` with reason
      ``"probe timeout exceeded backend budget"`` — never faked.
    * Each :func:`probe_one` already carries its own 2 s TCP timeout
      and 2 s HTTP timeout; the outer budget is the safety net for
      DNS stalls on ``*.local`` hostnames where stdlib timeouts don't
      bound the resolver.
    """
    specs: tuple[ServiceSpec, ...] = (*KNOWN_SERVICES, *extra)
    if not specs:
        return []
    results: list[ProbeResult | None] = [None] * len(specs)
    deadline = time.monotonic() + PROBE_ALL_DEADLINE_S
    max_workers = min(len(specs), 32) or 1
    # Do NOT use ``with ThreadPoolExecutor(...)`` here: ``__exit__`` calls
    # ``shutdown(wait=True)`` which blocks on stuck worker threads (e.g.
    # a DNS resolver call that won't return within the parallel-probe
    # budget). We call ``shutdown(wait=False, cancel_futures=True)``
    # manually so the outer budget really does bound wall-clock latency.
    pool = ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix="hermes-health-probe"
    )
    try:
        future_to_index = {
            pool.submit(probe_one, spec, PROBE_PER_TASK_TIMEOUT_S): idx
            for idx, spec in enumerate(specs)
        }
        try:
            for future in as_completed(future_to_index, timeout=PROBE_ALL_DEADLINE_S):
                idx = future_to_index[future]
                try:
                    results[idx] = future.result(timeout=0)
                except Exception as exc:  # noqa: BLE001 — bound every probe
                    results[idx] = _placeholder_result(
                        specs[idx], f"probe raised: {exc.__class__.__name__}"
                    )
        except TimeoutError:
            # Outer budget exhausted; remaining None slots become honest-unreachable.
            pass
    finally:
        # ``cancel_futures=True`` (Python 3.9+) prevents pending submissions
        # from running; ``wait=False`` returns immediately rather than
        # blocking on stuck ``socket.getaddrinfo`` threads. The leaked
        # worker threads will resolve on their own and discard their
        # results; the next request gets a fresh pool. Slightly wasteful,
        # but deterministically bounded — which is the whole point.
        pool.shutdown(wait=False, cancel_futures=True)
    now = time.monotonic()
    timed_out_reason = (
        "probe timeout exceeded backend budget"
        if now >= deadline
        else "probe did not return a result"
    )
    return [
        result if result is not None else _placeholder_result(specs[idx], timed_out_reason)
        for idx, result in enumerate(results)
    ]


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
                http_health_path="/server/info",
            )
        )
    return tuple(specs)
