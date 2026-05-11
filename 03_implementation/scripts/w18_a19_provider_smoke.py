#!/usr/bin/env python3
"""W18-A19 — live MiniMax + DeepSeek provider smoke probe.

Mission (operator-corrected verdict criteria, 2026-05-11):
    GUI_AGENT_WORKFLOW_GREEN final PASS_REAL requires at least one *live*
    MiniMax or DeepSeek backed assistive task. LM Studio / Ollama are local
    fallback only.

Hard rules enforced by this script:
  * NO API key values are ever logged, echoed, printed, returned, or written
    to disk. Only `key_present=true|false` booleans are surfaced.
  * Smallest-possible smoke: ``max_tokens=1`` (1-token completion).
  * Per provider we record ONLY: provider_id, model, proof_id, status,
    latency_ms, timestamp_utc, tokens_in, tokens_out. The raw response body
    is hashed (sha256) and stored as a hex digest, never the raw text.
  * If a key is missing we mark ``FAIL_KEY_MISSING`` honestly. No mocks,
    no skips, no fake passes.
  * Keys are read from ``G:/private/.env`` per the secret-storage convention.
  * NO printer hardware writes. (Smoke calls are HTTPS only.)

Output:
  03_implementation/var/agents/providers/smoke_<provider>_<timestamp>.json
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error

# -------------------------------------------------------------------------
# Path resolution. Script lives at 03_implementation/scripts/ — proof goes
# to 03_implementation/var/agents/providers/.
# -------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_IMPL_ROOT = _HERE.parents[1]
_PROOF_DIR = _IMPL_ROOT / "var" / "agents" / "providers"
_PRIVATE_ENV = Path(r"G:\private\.env")


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")


def _load_private_env(path: Path = _PRIVATE_ENV) -> dict[str, str]:
    """Read G:/private/.env into a dict WITHOUT printing values.

    Mirrors ``python-dotenv``'s minimal parser so we do not pull in an
    extra dep just for this smoke. Returns ``{}`` if the file is missing.
    """
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        out[key] = value
        # Mirror into os.environ so downstream code that calls os.environ.get
        # picks the value up. STILL never log it.
        os.environ.setdefault(key, value)
    return out


def _resolve_key(env: dict[str, str], names: tuple[str, ...]) -> str | None:
    """Return the first non-empty key value (still never logged)."""
    for name in names:
        v = os.environ.get(name) or env.get(name)
        if v:
            return v
    return None


def _post_json(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: float = 15.0,
) -> tuple[int, str, int]:
    """POST JSON. Returns (http_status, body_text, latency_ms).

    Uses stdlib urllib so we don't drag httpx into the smoke path. The
    Authorization header is BUILT here but never echoed to disk or stdout.
    """
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    started = time.monotonic_ns()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            text = exc.read().decode("utf-8", errors="replace")
        except Exception:
            text = ""
    except urllib.error.URLError as exc:
        # Network / DNS / TLS failure. Report status=0, reason in body.
        status = 0
        text = f"URLError reason={type(exc).__name__}"
    latency_ms = (time.monotonic_ns() - started) // 1_000_000
    return status, text, int(latency_ms)


def _safe_parse_completion(
    text: str,
    provider_id: str,
) -> dict[str, Any]:
    """Extract metadata from the response body without leaking content.

    We capture:
      - ``model`` echoed back
      - ``tokens_in`` / ``tokens_out`` usage counters
      - sha256 of the raw body (NOT the body itself)

    We deliberately DO NOT capture the generated text. A 1-token completion
    would normally be a single letter, but the operator forbids storing it.
    """
    body_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    meta: dict[str, Any] = {
        "body_sha256": body_sha,
        "body_size_bytes": len(text.encode("utf-8")),
    }
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return meta
    if not isinstance(parsed, dict):
        return meta
    meta["model"] = parsed.get("model")
    usage = parsed.get("usage")
    if isinstance(usage, dict):
        meta["tokens_in"] = usage.get("prompt_tokens")
        meta["tokens_out"] = usage.get("completion_tokens")
    # Capture error code/type for honest failure reporting (no secret leak).
    err = parsed.get("error")
    if isinstance(err, dict):
        meta["error_code"] = err.get("code") or err.get("type")
    return meta


def smoke_minimax(env: dict[str, str], *, dry: bool = False) -> dict[str, Any]:
    """Run a 1-token MiniMax smoke. Returns a dict safe to persist."""
    proof_id = f"smoke-minimax-{uuid.uuid4().hex[:12]}"
    timestamp = _utc_iso()
    key_names = (
        "HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY",
        "MINIMAX_TOKEN_PLAN_API_KEY",
        "HERMES3D_MINIMAX_HIGHSPEED_API_KEY",
        "MINIMAX_HIGHSPEED_API_KEY",
        "HERMES3D_MINIMAX_API_KEY",
        "MINIMAX_API_KEY",
    )
    key = _resolve_key(env, key_names)
    base_url = (
        os.environ.get("HERMES3D_MINIMAX_BASE_URL")
        or os.environ.get("MINIMAX_BASE_URL")
        or "https://api.minimax.io/v1"
    )
    model = (
        os.environ.get("HERMES3D_MINIMAX_MODEL")
        or os.environ.get("MINIMAX_MODEL")
        or "MiniMax-M2"
    )
    result: dict[str, Any] = {
        "proof_id": proof_id,
        "provider_id": "minimax",
        "model": model,
        "base_url": base_url,
        "key_present": bool(key),
        "timestamp_utc": timestamp,
        "smoke_max_tokens": 1,
    }
    if not key:
        result["status"] = "FAIL_KEY_MISSING"
        result["http_status"] = None
        result["latency_ms"] = 0
        return result
    if dry:
        result["status"] = "DRY_RUN"
        result["http_status"] = None
        result["latency_ms"] = 0
        return result
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "1"}],
        "max_tokens": 1,
    }
    status, text, latency_ms = _post_json(url, headers, body)
    meta = _safe_parse_completion(text, "minimax")
    result["http_status"] = status
    result["latency_ms"] = latency_ms
    result["response_meta"] = meta
    if 200 <= status < 300:
        result["status"] = "PASS_LIVE"
    elif status == 0:
        result["status"] = "FAIL_NETWORK"
    elif status in (401, 403):
        result["status"] = "FAIL_AUTH"
    elif status == 429:
        result["status"] = "FAIL_RATE_LIMIT"
    elif 400 <= status < 500:
        result["status"] = "FAIL_REQUEST"
    else:
        result["status"] = "FAIL_UPSTREAM"
    return result


def smoke_deepseek(env: dict[str, str], *, dry: bool = False) -> dict[str, Any]:
    """Run a 1-token DeepSeek smoke. Returns a dict safe to persist."""
    proof_id = f"smoke-deepseek-{uuid.uuid4().hex[:12]}"
    timestamp = _utc_iso()
    key_names = (
        "HERMES3D_DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEY",
    )
    key = _resolve_key(env, key_names)
    base_url = (
        os.environ.get("HERMES3D_DEEPSEEK_BASE_URL")
        or os.environ.get("DEEPSEEK_BASE_URL")
        or "https://api.deepseek.com/v1"
    )
    model = (
        os.environ.get("HERMES3D_DEEPSEEK_MODEL")
        or os.environ.get("DEEPSEEK_MODEL")
        or "deepseek-chat"
    )
    result: dict[str, Any] = {
        "proof_id": proof_id,
        "provider_id": "deepseek",
        "model": model,
        "base_url": base_url,
        "key_present": bool(key),
        "timestamp_utc": timestamp,
        "smoke_max_tokens": 1,
    }
    if not key:
        result["status"] = "FAIL_KEY_MISSING"
        result["http_status"] = None
        result["latency_ms"] = 0
        return result
    if dry:
        result["status"] = "DRY_RUN"
        result["http_status"] = None
        result["latency_ms"] = 0
        return result
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "1"}],
        "max_tokens": 1,
    }
    status, text, latency_ms = _post_json(url, headers, body)
    meta = _safe_parse_completion(text, "deepseek")
    result["http_status"] = status
    result["latency_ms"] = latency_ms
    result["response_meta"] = meta
    if 200 <= status < 300:
        result["status"] = "PASS_LIVE"
    elif status == 0:
        result["status"] = "FAIL_NETWORK"
    elif status in (401, 403):
        result["status"] = "FAIL_AUTH"
    elif status == 429:
        result["status"] = "FAIL_RATE_LIMIT"
    elif 400 <= status < 500:
        result["status"] = "FAIL_REQUEST"
    else:
        result["status"] = "FAIL_UPSTREAM"
    return result


def _write_proof(result: dict[str, Any]) -> Path:
    _PROOF_DIR.mkdir(parents=True, exist_ok=True)
    provider = result["provider_id"]
    ts = result["timestamp_utc"].replace(":", "").replace("-", "").replace(".", "")
    path = _PROOF_DIR / f"smoke_{provider}_{ts}.json"
    # Belt-and-braces: strip anything that even *looks* like a key from the
    # persisted blob. We never put one in, but defense in depth.
    redacted = {k: v for k, v in result.items() if "key" not in k.lower() or k == "key_present"}
    path.write_text(json.dumps(redacted, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    dry = "--dry" in args
    only = None
    for a in args:
        if a.startswith("--only="):
            only = a.split("=", 1)[1].strip().lower()
    env = _load_private_env()
    summary: dict[str, Any] = {
        "task_id": "W18-A19-PROVIDER-LIVE-SMOKE-2026-05-11",
        "timestamp_utc": _utc_iso(),
        "dry_run": dry,
        "providers": {},
    }
    if only in (None, "minimax"):
        mm = smoke_minimax(env, dry=dry)
        proof_path = _write_proof(mm)
        mm["smoke_proof_path"] = str(proof_path.relative_to(_IMPL_ROOT.parent)).replace("\\", "/")
        summary["providers"]["minimax"] = mm
    if only in (None, "deepseek"):
        ds = smoke_deepseek(env, dry=dry)
        proof_path = _write_proof(ds)
        ds["smoke_proof_path"] = str(proof_path.relative_to(_IMPL_ROOT.parent)).replace("\\", "/")
        summary["providers"]["deepseek"] = ds
    # NEVER print the env dict or any keys. Print only the summary.
    print(json.dumps(summary, indent=2, sort_keys=True))
    # Exit 0 even on FAIL — failure is recorded honestly in the proof.
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
