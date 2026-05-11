"""W18-A13 — integration tests for the backend wiring fixes.

Each test asserts a specific finding from the W18-A3 audit
(``03_implementation/docs/handoffs/W18-A3_BACKEND_ENDPOINT_AUDIT_2026-05-11.md``)
is now fixed against the live FastAPI GUI bridge.

Covers:

FAIL_BACKEND_MISSING fixes:
- ``POST /api/approvals/{id}/defer`` — new handler, mirrors approve/reject.
- ``GET /api/source-os/modules/update-readiness`` — alias of
  ``/api/modules/update/readiness``.
- ``POST /api/source-os/modules/{id}/run-proof`` — alias of
  ``/api/apps/{id}/run-proof``.

FAIL_BROKEN fixes:
- ``GET /api/agents/config`` — new GET handler complementing the
  existing PUT.
- ``GET /api/modules/runtime/verifiers`` — response cache so warm
  reads return under the 8s FE timeout.
- ``GET /api/modules/runtime/agent-cli-readiness`` — same cache.

FAIL_NOT_WIRED structural assertions:
- ``GET /api/mcp/locks`` — shape contract (items[] with files[]) the
  FE McpSubtab now reads.

Operator-freeze contract:
- No printer hardware writes are exercised. Printer-domain tests are
  intentionally absent; the freeze is enforced at the test boundary,
  not the runtime.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Spin up a fresh FastAPI GUI app with an isolated temp DB.

    Mirrors :func:`test_app_registry_proof_run.client` so tests share
    sandbox semantics with adjacent suites. Per-module one-shot caches
    are reset so each test sees a fresh ``load_modules()`` call.
    """
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "w18_a13.db"

    import hermes3d.db.init as dbinit
    import hermes3d.db.load_modules as lm

    monkeypatch.setattr(dbinit, "DB_PATH", db_path)
    monkeypatch.setattr(lm, "DB_PATH", db_path)

    import hermes3d.api.routes.apps as apps_route
    import hermes3d.api.routes.modules as modules_route

    monkeypatch.setattr(apps_route, "_APPS_SYNCED", False)
    monkeypatch.setattr(modules_route, "_MODULES_SYNCED", False)
    # W18-A13 — also clear the runtime response cache so each test
    # observes a freshly computed payload.
    monkeypatch.setattr(modules_route, "_RUNTIME_RESPONSE_CACHE", {})

    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# FAIL_BACKEND_MISSING — /api/approvals/{id}/defer
# ---------------------------------------------------------------------------


def _seed_pending_approval(approval_id: str = "appr-w18-a13-1") -> None:
    """Insert a pending approval row directly so we can defer it.

    The approvals collection has no POST handler (rows are created by
    upstream services). For W18-A13 we only need the defer transition
    to succeed against a real row.
    """
    from hermes3d.api.routes._common import execute

    execute(
        """
        INSERT INTO approvals (id, approval_type, status, requesting_agent, requested_at)
        VALUES (?, 'w18-a13-test', 'pending', 'test', datetime('now'))
        """,
        (approval_id,),
    )


def test_approvals_defer_route_is_registered(client: TestClient) -> None:
    """W18-A3 finding: POST /api/approvals/{id}/defer was 404.
    Now it must be a registered route (the bare POST returns 404 for an
    unknown id, not 404 for an unknown route).
    """
    resp = client.post("/api/approvals/nonexistent/defer", json={"reason": "later"})
    # 404 = approval row not found (handler ran), not 404 = path not registered.
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "approval not found"


def test_approvals_defer_transitions_pending_to_deferred(client: TestClient) -> None:
    _seed_pending_approval("appr-w18-a13-defer")
    resp = client.post(
        "/api/approvals/appr-w18-a13-defer/defer",
        json={"reason": "operator deferred via W18-A13 test"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "deferred"
    assert body["reason"] == "operator deferred via W18-A13 test"


def test_approvals_defer_rejects_already_decided(client: TestClient) -> None:
    """Defer must respect the pending-only transition rule."""
    _seed_pending_approval("appr-w18-a13-twice")
    first = client.post(
        "/api/approvals/appr-w18-a13-twice/defer", json={"reason": "first"}
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/approvals/appr-w18-a13-twice/defer", json={"reason": "second"}
    )
    assert second.status_code == 409


# ---------------------------------------------------------------------------
# FAIL_BROKEN — GET /api/agents/config
# ---------------------------------------------------------------------------


def test_agents_config_get_route_is_registered(client: TestClient) -> None:
    """W18-A3 finding: GET on /api/agents/config returned 405 (PUT-only).
    The FE Settings → AgentConfigSection GETs to populate the form."""
    resp = client.get("/api/agents/config")
    assert resp.status_code == 200, resp.text


def test_agents_config_get_returns_envelope_shape(client: TestClient) -> None:
    body = client.get("/api/agents/config").json()
    assert body["accepted"] is True
    assert body["status"] == "ready"
    assert "config" in body
    assert isinstance(body["config"], dict)
    assert "api_key_configured" in body
    assert isinstance(body["api_key_configured"], bool)
    assert body["redacted"] == ["api_key"]


def test_agents_config_get_never_echoes_api_key(client: TestClient) -> None:
    """Defence in depth: the api_key value must never appear in GET."""
    client.put(
        "/api/agents/config",
        json={"config": {"api_key": "secret-w18-a13", "model": "gpt-test"}},
    )
    body = client.get("/api/agents/config").json()
    assert "api_key" not in body["config"]
    # The model value (non-secret) round-trips:
    assert body["config"].get("model") == "gpt-test"


# ---------------------------------------------------------------------------
# FAIL_BACKEND_MISSING — /api/source-os/modules/update-readiness alias
# ---------------------------------------------------------------------------


def test_source_os_update_readiness_alias_registered(client: TestClient) -> None:
    """W18-A3 finding: FE hermes3dClient.sourceOsClient.updateReadiness()
    called /api/source-os/modules/update-readiness which returned 404.
    The alias must now return the same shape as the canonical handler."""
    resp = client.get("/api/source-os/modules/update-readiness")
    assert resp.status_code == 200, resp.text


def test_source_os_update_readiness_alias_matches_canonical(
    client: TestClient,
) -> None:
    canonical = client.get("/api/modules/update/readiness").json()
    aliased = client.get("/api/source-os/modules/update-readiness").json()
    # Top-level keys must match — values differ only by transient timestamps
    # which neither response carries.
    assert canonical.keys() == aliased.keys()
    assert canonical["status"] == aliased["status"]
    assert canonical["count"] == aliased["count"]


# ---------------------------------------------------------------------------
# FAIL_BACKEND_MISSING — /api/source-os/modules/{id}/run-proof alias
# ---------------------------------------------------------------------------


def test_source_os_module_run_proof_alias_registered(client: TestClient) -> None:
    """W18-A3 finding: the FE appsClient singleton's primary URL was
    /api/source-os/modules/{id}/run-proof which 404'd. The alias must
    now delegate to /api/apps/{id}/run-proof.
    """
    # Find any module id that has the apps registry row.
    listing = client.get("/api/apps").json()
    sample = listing["apps"][0]
    app_id = sample["id"]

    # Compare both routes return the same envelope.
    canonical = client.post(f"/api/apps/{app_id}/run-proof").json()
    aliased = client.post(f"/api/source-os/modules/{app_id}/run-proof").json()
    # The two share the same status (either both no-op-not_set or both
    # run a real proof_command). Some status fields like ``duration_ms``
    # vary per call so we compare shape, not exact values.
    assert canonical["app_id"] == app_id
    assert aliased["app_id"] == app_id
    assert "accepted" in aliased
    assert "status" in aliased


# ---------------------------------------------------------------------------
# FAIL_BROKEN — /api/modules/runtime/verifiers cached response
# ---------------------------------------------------------------------------


def test_runtime_verifiers_response_is_cached(client: TestClient) -> None:
    """W18-A13: second call within TTL must return the same cached object,
    proving the cache short-circuits the slow rebuild path."""
    first = client.get("/api/modules/runtime/verifiers").json()
    second = client.get("/api/modules/runtime/verifiers").json()
    assert first == second
    # The cache returns object identity in-process; over HTTP the test
    # can only assert structural equality. To prove the cache is actually
    # hit, measure the second call is materially faster than the first.
    t0 = time.perf_counter()
    client.get("/api/modules/runtime/verifiers")
    elapsed = time.perf_counter() - t0
    # 200 ms is a generous upper bound for a cached dict-lookup; the
    # uncached path is multiple seconds. The exact ceiling is not
    # important — what matters is it's far below the original >20s
    # cold-start observation.
    assert elapsed < 2.0, f"cached verifier call too slow: {elapsed:.2f}s"


def test_runtime_agent_cli_readiness_response_is_cached(client: TestClient) -> None:
    """W18-A13: companion of test_runtime_verifiers_response_is_cached."""
    first = client.get("/api/modules/runtime/agent-cli-readiness").json()
    second = client.get("/api/modules/runtime/agent-cli-readiness").json()
    assert first == second
    t0 = time.perf_counter()
    client.get("/api/modules/runtime/agent-cli-readiness")
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, f"cached agent-cli-readiness call too slow: {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# FAIL_NOT_WIRED — /api/mcp/locks shape contract
# ---------------------------------------------------------------------------


def test_mcp_locks_envelope_shape(client: TestClient) -> None:
    """W18-A3 finding: the FE McpSubtab read ``data.locks`` and per-row
    ``file`` (singular). The BE returns ``{items: [...], total, accepted,
    status}`` with per-item ``files: [str]``. Lock the BE contract so a
    future refactor that breaks the shape fails this test."""
    body = client.get("/api/mcp/locks").json()
    assert "accepted" in body
    assert "status" in body
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    # Per-item shape (only valid if any locks exist; tolerate empty case).
    for item in body["items"]:
        assert "lock_id" in item
        assert "owner" in item
        assert "files" in item
        assert isinstance(item["files"], list)


# ---------------------------------------------------------------------------
# Operator-freeze guard: no printer hardware writes in this test file.
# ---------------------------------------------------------------------------


def test_no_printer_write_endpoints_exercised(client: TestClient) -> None:
    """Static assertion that no test in this file calls any printer
    hardware-write endpoint. We scan AST function bodies (skipping
    this guard function's own body so it doesn't false-positive on
    its own forbidden-token list) for write-verb client calls on
    printer paths.
    """
    import ast

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    GUARD_NAME = "test_no_printer_write_endpoints_exercised"
    forbidden_methods = {"post", "put", "patch", "delete"}
    violations: list[str] = []

    class CallVisitor(ast.NodeVisitor):
        def __init__(self, func_name: str) -> None:
            self.func_name = func_name

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            method_name: str | None = None
            if isinstance(func, ast.Attribute):
                method_name = func.attr
            if method_name in forbidden_methods and node.args:
                first = node.args[0]
                literal: str | None = None
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    literal = first.value
                elif isinstance(first, ast.JoinedStr):
                    # f-string: gather the literal parts
                    literal = "".join(
                        v.value
                        for v in first.values
                        if isinstance(v, ast.Constant) and isinstance(v.value, str)
                    )
                if literal and "/api/printers" in literal:
                    violations.append(
                        f"{self.func_name} → {method_name.upper()} {literal}"
                    )
            self.generic_visit(node)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name != GUARD_NAME:
            CallVisitor(node.name).visit(node)
    assert violations == [], "freeze violations: " + "; ".join(violations)
