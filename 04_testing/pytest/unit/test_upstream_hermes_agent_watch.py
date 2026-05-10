"""Unit tests for 03_implementation/scripts/upstream_hermes_agent_watch.py.

All network is mocked — never calls api.github.com. Verifies the three
sub-checks (tag-gt-min, sustained-5-distinct-shas, PR successor) and the
combined `evaluate()` aggregator.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Repo-root from 04_testing/pytest/unit/test_X.py = parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "03_implementation" / "scripts" / "upstream_hermes_agent_watch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("upstream_hermes_agent_watch", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["upstream_hermes_agent_watch"] = mod
    spec.loader.exec_module(mod)
    return mod


watcher = _load_module()


# ---------- pure helpers --------------------------------------------------------------


def test_parse_tag_strips_v_prefix():
    assert watcher.parse_tag("v2026.5.8") == (2026, 5, 8)
    assert watcher.parse_tag("2026.5.7") == (2026, 5, 7)
    assert watcher.parse_tag("v0.14.0") == (0, 14, 0)


def test_parse_tag_rejects_garbage():
    assert watcher.parse_tag("not-a-tag") is None
    assert watcher.parse_tag("v0.14.0-rc1") is None
    assert watcher.parse_tag("") is None


def test_latest_tag_exceeds_min_pass():
    tags = [{"name": "v2026.5.7"}, {"name": "v2026.5.8"}, {"name": "v2026.5.6"}]
    ok, top = watcher.latest_tag_exceeds_min(tags, (2026, 5, 7))
    assert ok is True
    assert top == "v2026.5.8"


def test_latest_tag_exceeds_min_fail_when_equal():
    tags = [{"name": "v2026.5.7"}, {"name": "v2026.5.6"}]
    ok, top = watcher.latest_tag_exceeds_min(tags, (2026, 5, 7))
    assert ok is False
    assert top == "v2026.5.7"


def test_latest_tag_exceeds_min_fail_no_parsable():
    ok, top = watcher.latest_tag_exceeds_min([{"name": "garbage"}], (2026, 5, 7))
    assert ok is False
    assert top is None


def test_sustained_distinct_shas_pass():
    runs = [
        {"conclusion": "success", "head_branch": "main", "head_sha": f"sha{i}"} for i in range(5)
    ]
    ok, shas = watcher.sustained_distinct_shas(runs, 5)
    assert ok is True
    assert len(shas) == 5
    assert len(set(shas)) == 5


def test_sustained_distinct_shas_fail_dup_shas():
    runs = [{"conclusion": "success", "head_branch": "main", "head_sha": "sha-x"} for _ in range(5)]
    ok, _shas = watcher.sustained_distinct_shas(runs, 5)
    assert ok is False


def test_sustained_distinct_shas_filters_non_main_and_failures():
    runs = [
        {"conclusion": "success", "head_branch": "feature", "head_sha": "a"},
        {"conclusion": "failure", "head_branch": "main", "head_sha": "b"},
        {"conclusion": "success", "head_branch": "main", "head_sha": "c"},
    ]
    ok, shas = watcher.sustained_distinct_shas(runs, 5)
    assert ok is False
    assert shas == ["c"]


def test_has_pr22567_successor_open():
    items = [{"state": "open", "html_url": "https://x/y/pull/9", "pull_request": {}}]
    ok, url = watcher.has_pr22567_successor(items)
    assert ok is True
    assert url == "https://x/y/pull/9"


def test_has_pr22567_successor_merged():
    items = [
        {
            "state": "closed",
            "html_url": "https://x/y/pull/8",
            "pull_request": {"merged_at": "2026-01-01T00:00:00Z"},
        }
    ]
    ok, url = watcher.has_pr22567_successor(items)
    assert ok is True
    assert url == "https://x/y/pull/8"


def test_has_pr22567_successor_closed_unmerged():
    items = [{"state": "closed", "html_url": "https://x/y/pull/7", "pull_request": {}}]
    ok, url = watcher.has_pr22567_successor(items)
    assert ok is False
    assert url is None


# ---------- evaluate() aggregator with urlopen mocked ------------------------------


class _FakeResp(io.BytesIO):
    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *_: Any) -> None:  # noqa: D401
        self.close()


def _resp(payload: Any) -> _FakeResp:
    return _FakeResp(json.dumps(payload).encode("utf-8"))


def _stub_urlopen(tags: list, runs: list, search_items: list):
    """Return a callable suitable for monkeypatching urllib.request.urlopen.

    Routes by URL substring so the script's three GETs each get the right payload.
    """

    def fake_urlopen(req, timeout=30):  # noqa: ARG001
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/tags" in url:
            return _resp(tags)
        if "/actions/workflows/" in url and "/runs" in url:
            return _resp({"workflow_runs": runs})
        if "/search/issues" in url:
            return _resp({"items": search_items})
        raise AssertionError(f"unexpected URL in test: {url}")

    return fake_urlopen


def test_evaluate_all_three_pass(monkeypatch):
    tags = [{"name": "v2026.5.10"}, {"name": "v2026.5.7"}]
    runs = [
        {"conclusion": "success", "head_branch": "main", "head_sha": f"sha{i}"} for i in range(5)
    ]
    items = [{"state": "open", "html_url": "https://github.com/x/y/pull/1", "pull_request": {}}]
    monkeypatch.setattr(watcher.urllib.request, "urlopen", _stub_urlopen(tags, runs, items))
    out = watcher.evaluate()
    assert out["all_three_hold"] is True
    assert out["tag_check"]["pass"] is True
    assert out["sustained_check"]["pass"] is True
    assert out["pr_check"]["pass"] is True


def test_evaluate_tag_only_fails(monkeypatch):
    tags = [{"name": "v2026.5.7"}]  # equal, not strictly greater
    runs = [
        {"conclusion": "success", "head_branch": "main", "head_sha": f"sha{i}"} for i in range(5)
    ]
    items = [{"state": "open", "html_url": "https://x/y/pull/1", "pull_request": {}}]
    monkeypatch.setattr(watcher.urllib.request, "urlopen", _stub_urlopen(tags, runs, items))
    out = watcher.evaluate()
    assert out["all_three_hold"] is False
    assert out["tag_check"]["pass"] is False


def test_evaluate_main_returns_zero_on_hit_one_on_miss(monkeypatch, capsys):
    # all-pass -> rc 0
    tags = [{"name": "v2026.5.20"}]
    runs = [
        {"conclusion": "success", "head_branch": "main", "head_sha": f"sha{i}"} for i in range(5)
    ]
    items = [{"state": "open", "html_url": "https://x/y/pull/1", "pull_request": {}}]
    monkeypatch.setattr(watcher.urllib.request, "urlopen", _stub_urlopen(tags, runs, items))
    assert watcher.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["all_three_hold"] is True

    # miss -> rc 1
    monkeypatch.setattr(watcher.urllib.request, "urlopen", _stub_urlopen([], runs, items))
    assert watcher.main() == 1


def test_token_header_added_when_env_set(monkeypatch):
    captured: dict[str, Any] = {}

    def cap_urlopen(req, timeout=30):  # noqa: ARG001
        captured["headers"] = dict(req.header_items())
        return _resp([])

    monkeypatch.setenv("GITHUB_TOKEN", "ghs_secret")
    monkeypatch.setattr(watcher.urllib.request, "urlopen", cap_urlopen)
    watcher._github_request("/repos/x/y/tags")
    headers_lower = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_lower.get("authorization") == "Bearer ghs_secret"


def test_token_header_absent_when_env_unset(monkeypatch):
    captured: dict[str, Any] = {}

    def cap_urlopen(req, timeout=30):  # noqa: ARG001
        captured["headers"] = dict(req.header_items())
        return _resp([])

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(watcher.urllib.request, "urlopen", cap_urlopen)
    watcher._github_request("/repos/x/y/tags")
    headers_lower = {k.lower(): v for k, v in captured["headers"].items()}
    assert "authorization" not in headers_lower


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
