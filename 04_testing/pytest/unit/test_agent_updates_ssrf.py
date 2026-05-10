"""Bonus 12 finding #5 (Audit PR #135): fail-closed on GitHub Releases outage.

Pre-fix: ``_remote_release_tags`` and ``_latest_release`` swallowed every
``Exception`` and returned ``[]`` / empty-tag, so DNS poison, MITM TLS,
GitHub 5xx, or rate-limit bans collapsed silently into
``status="already_current"`` downstream — masking a stale Hermes Agent
checkout (CWE-918 / OWASP CICD-SEC-1 fail-open).

Post-fix: tighten except to known network/parse failure modes only;
raise ``HTTPException(502)`` with a ``_redact()``-cleaned detail on real
outages. ``_latest_release`` keeps a soft-warning fast-path for HTTP 404
(repo has no releases yet).

References:
- https://docs.python.org/3/library/urllib.error.html
- https://cwe.mitre.org/data/definitions/918.html
- https://owasp.org/www-project-top-10-ci-cd-security-risks/
"""

from __future__ import annotations

import json
import socket
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from hermes3d.api.routes import agent_updates

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _FakeResp:
    """Minimal urllib.response shim — supports context manager + .read()."""

    def __init__(self, body: str) -> None:
        self._b = body.encode("utf-8")

    def read(self) -> bytes:
        return self._b

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


# ---------------------------------------------------------------------------
# _remote_release_tags — happy path
# ---------------------------------------------------------------------------


def test_remote_release_tags_success(tmp_path: Path) -> None:
    """200 + valid tag list returns sorted unique tags."""
    body = json.dumps(
        [
            {"tag_name": "v2026.5.7"},
            {"tag_name": "v2026.4.1"},
            {"tag_name": "garbage-not-a-tag"},
        ]
    )
    with patch.object(agent_updates.urllib.request, "urlopen", return_value=_FakeResp(body)):
        tags = agent_updates._remote_release_tags(tmp_path)
    assert tags == ["v2026.4.1", "v2026.5.7"]


def test_remote_release_tags_empty_list_returns_empty(tmp_path: Path) -> None:
    """200 + ``[]`` (repo with no releases yet) is NOT an error path."""
    with patch.object(agent_updates.urllib.request, "urlopen", return_value=_FakeResp("[]")):
        tags = agent_updates._remote_release_tags(tmp_path)
    assert tags == [], "Genuinely empty release list must NOT raise; only outages do."


# ---------------------------------------------------------------------------
# _remote_release_tags — fail-closed on real outages (Bonus 12 #5)
# ---------------------------------------------------------------------------


def test_remote_release_tags_network_timeout_raises_502(tmp_path: Path) -> None:
    """socket.timeout from urlopen must surface as HTTPException 502."""
    with patch.object(
        agent_updates.urllib.request, "urlopen", side_effect=socket.timeout("read timed out")
    ):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._remote_release_tags(tmp_path)
    assert exc_info.value.status_code == 502
    assert "unreachable" in str(exc_info.value.detail).lower()


def test_remote_release_tags_url_error_raises_502(tmp_path: Path) -> None:
    """urllib.error.URLError (DNS / refused) → 502."""
    with patch.object(
        agent_updates.urllib.request,
        "urlopen",
        side_effect=urllib.error.URLError("nodename nor servname provided"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._remote_release_tags(tmp_path)
    assert exc_info.value.status_code == 502


def test_remote_release_tags_5xx_raises_502(tmp_path: Path) -> None:
    """HTTPError(503) (subclass of URLError) must also surface as 502."""
    err = urllib.error.HTTPError(agent_updates.RELEASES_API, 503, "Service Unavailable", {}, None)
    with patch.object(agent_updates.urllib.request, "urlopen", side_effect=err):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._remote_release_tags(tmp_path)
    assert exc_info.value.status_code == 502


def test_remote_release_tags_malformed_json_raises_502(tmp_path: Path) -> None:
    """Non-JSON response body → 502 (upstream contract violation)."""
    with patch.object(agent_updates.urllib.request, "urlopen", return_value=_FakeResp("{not-json")):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._remote_release_tags(tmp_path)
    assert exc_info.value.status_code == 502


def test_remote_release_tags_non_list_payload_raises_502(tmp_path: Path) -> None:
    """200 + {object} (instead of list) → 502 (contract violation)."""
    body = json.dumps({"message": "Not Found", "status": "404"})
    with patch.object(agent_updates.urllib.request, "urlopen", return_value=_FakeResp(body)):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._remote_release_tags(tmp_path)
    assert exc_info.value.status_code == 502
    assert "non-list" in str(exc_info.value.detail).lower()


# ---------------------------------------------------------------------------
# redact_text applied to error detail (no secret leakage in 502 body)
# P1-8 F3 (2026-05-09): the legacy local ``_redact()`` (which produced
# ``Bearer [REDACTED]``) was replaced with the gateway ``redact_text``
# (which produces ``Bearer ***`` for the same input). Both contracts
# guarantee the secret is gone; this test pins the new marker shape so
# a future regression to the legacy helper would fail.
# ---------------------------------------------------------------------------


def test_remote_release_tags_redacts_bearer_in_detail(tmp_path: Path) -> None:
    """Any bearer-shaped string in the exception message must be redacted."""
    err = urllib.error.URLError("connection refused: Bearer abc123secret-do-not-leak")
    with patch.object(agent_updates.urllib.request, "urlopen", side_effect=err):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._remote_release_tags(tmp_path)
    detail = str(exc_info.value.detail)
    # Cleartext gone — the security contract.
    assert "abc123secret-do-not-leak" not in detail
    # ``redact_text`` collapses ``Bearer xxx`` to ``Bearer ***``.
    assert "Bearer ***" in detail


# ---------------------------------------------------------------------------
# _latest_release behavior: 404 is soft, other failures are hard
# ---------------------------------------------------------------------------


def test_latest_release_404_keeps_soft_warning() -> None:
    """HTTP 404 = repo has no /releases/latest yet — preserve soft warning."""
    err = urllib.error.HTTPError(agent_updates.LATEST_RELEASE_API, 404, "Not Found", {}, None)
    with patch.object(agent_updates.urllib.request, "urlopen", side_effect=err):
        out = agent_updates._latest_release(tags=[])
    assert out["tag"] is None
    assert "404" in out.get("api_warning", "")


def test_latest_release_5xx_raises_502() -> None:
    """HTTP 503 (any non-404 HTTPError) → HTTPException 502."""
    err = urllib.error.HTTPError(
        agent_updates.LATEST_RELEASE_API, 503, "Service Unavailable", {}, None
    )
    with patch.object(agent_updates.urllib.request, "urlopen", side_effect=err):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._latest_release(tags=[])
    assert exc_info.value.status_code == 502


def test_latest_release_url_error_keeps_soft_warning() -> None:
    """URLError (e.g. transient DNS) on latest endpoint → soft warning, NOT 502.

    Rationale: ``_remote_release_tags`` is the authoritative gate. If we got
    this far, tags came back successfully, so a transient hiccup on the
    latest endpoint is acceptable.
    """
    with patch.object(
        agent_updates.urllib.request,
        "urlopen",
        side_effect=urllib.error.URLError("transient hiccup"),
    ):
        out = agent_updates._latest_release(tags=["v2026.5.7"])
    assert out["tag"] is None
    assert out.get("api_warning"), "URLError on latest must populate api_warning"


def test_latest_release_success() -> None:
    """200 + valid latest payload populates the result."""
    body = json.dumps(
        {
            "tag_name": "v2026.5.7",
            "name": "Tenacity Release",
            "published_at": "2026-05-07T00:00:00Z",
            "html_url": "https://example.invalid/v2026.5.7",
        }
    )
    with patch.object(agent_updates.urllib.request, "urlopen", return_value=_FakeResp(body)):
        out = agent_updates._latest_release(tags=["v2026.5.7"])
    assert out["tag"] == "v2026.5.7"
    assert out["name"] == "Tenacity Release"
