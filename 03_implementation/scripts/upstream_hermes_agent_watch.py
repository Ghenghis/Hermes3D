"""Weekly cron watcher for NousResearch/hermes-agent upstream readiness.

Three-condition trigger (matches Wave A1 sustained-5 heuristic):

  1. Latest tag on `NousResearch/hermes-agent` is strictly greater than
     v2026.5.7 (e.g. v2026.5.8, v2026.5.10, v0.14.0).
  2. The last 5 successful runs of the upstream `Tests` workflow
     (workflow_id 242054771) on `main` cover 5 distinct head_shas.
  3. A successor to PR #22567 exists in OPEN/MERGED state matching the
     query `windows skip tests OR pwd fcntl skip` (a working signal that
     upstream is finally serious about Windows + macOS support).

If all three hold, the script writes a JSON evidence payload to stdout
and a workflow can use it to open a tracking issue.

Pure stdlib only: `urllib.request`, `json`, `os`, `re`, `sys`. No
`requests` dep. Reads optional `GITHUB_TOKEN` for higher rate limits;
falls back to anon (60 req/h, plenty for one weekly run).
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

GITHUB_API = "https://api.github.com"
UPSTREAM_REPO = "NousResearch/hermes-agent"
TESTS_WORKFLOW_ID = 242054771
TARGET_REPO = "Ghenghis/Hermes3D"
MIN_TAG = (2026, 5, 7)
PR_QUERY_TERMS = "windows skip tests OR pwd fcntl skip"
USER_AGENT = "hermes3d-upstream-watcher/1.0"


def _github_request(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET an api.github.com path. Returns parsed JSON, raises on HTTP error."""
    url = f"{GITHUB_API}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - https only
        return json.loads(resp.read().decode("utf-8"))


def parse_tag(name: str) -> tuple[int, ...] | None:
    """Parse 'v2026.5.8' / 'v0.14.0' / '2026.5.7' -> tuple of ints. None if no match."""
    m = re.match(r"^v?(\d+(?:\.\d+)*)$", name.strip())
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def latest_tag_exceeds_min(
    tags: list[dict[str, Any]], min_tag: tuple[int, ...]
) -> tuple[bool, str | None]:
    """Return (passes, latest_name). True iff any parsed tag > min_tag."""
    parsed: list[tuple[tuple[int, ...], str]] = []
    for t in tags:
        name = str(t.get("name", ""))
        v = parse_tag(name)
        if v is not None:
            parsed.append((v, name))
    if not parsed:
        return False, None
    parsed.sort(reverse=True)
    top_ver, top_name = parsed[0]
    return (top_ver > min_tag), top_name


def sustained_distinct_shas(runs: list[dict[str, Any]], n: int = 5) -> tuple[bool, list[str]]:
    """True iff the first `n` successful main-branch runs cover n distinct head_shas."""
    successful = [
        r for r in runs if r.get("conclusion") == "success" and r.get("head_branch") == "main"
    ]
    head_shas = [str(r.get("head_sha", "")) for r in successful[:n]]
    return (len(set(head_shas)) >= n and len(head_shas) >= n), head_shas


def has_pr22567_successor(items: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """True iff any open/merged PR (state != closed-without-merge) matches the query."""
    for it in items:
        state = it.get("state", "")
        merged = bool(it.get("pull_request", {}).get("merged_at"))
        if state == "open" or merged:
            return True, str(it.get("html_url") or "")
    return False, None


def evaluate() -> dict[str, Any]:
    """Run the 3 checks and return evidence dict."""
    tags = _github_request(f"/repos/{UPSTREAM_REPO}/tags", {"per_page": 30})
    tag_pass, latest_tag = latest_tag_exceeds_min(tags, MIN_TAG)

    runs_resp = _github_request(
        f"/repos/{UPSTREAM_REPO}/actions/workflows/{TESTS_WORKFLOW_ID}/runs",
        {"branch": "main", "status": "success", "per_page": 10},
    )
    runs = runs_resp.get("workflow_runs", []) if isinstance(runs_resp, dict) else []
    sustained_pass, head_shas = sustained_distinct_shas(runs, 5)

    pr_query = f"repo:{UPSTREAM_REPO} is:pr ({PR_QUERY_TERMS})"
    pr_resp = _github_request("/search/issues", {"q": pr_query, "per_page": 5})
    items = pr_resp.get("items", []) if isinstance(pr_resp, dict) else []
    pr_pass, pr_url = has_pr22567_successor(items)

    return {
        "all_three_hold": tag_pass and sustained_pass and pr_pass,
        "tag_check": {
            "pass": tag_pass,
            "latest_tag": latest_tag,
            "url": f"https://github.com/{UPSTREAM_REPO}/tags",
        },
        "sustained_check": {
            "pass": sustained_pass,
            "head_shas": head_shas,
            "url": f"https://github.com/{UPSTREAM_REPO}/actions/workflows/{TESTS_WORKFLOW_ID}",
        },
        "pr_check": {
            "pass": pr_pass,
            "matching_pr_url": pr_url,
            "url": f"https://github.com/{UPSTREAM_REPO}/pulls?q=is%3Apr+{urllib.parse.quote_plus(PR_QUERY_TERMS)}",
        },
        "target_repo": TARGET_REPO,
    }


def main() -> int:
    try:
        result = evaluate()
    except urllib.error.HTTPError as exc:
        print(
            json.dumps({"error": f"HTTP {exc.code}: {exc.reason}", "url": exc.url}), file=sys.stderr
        )
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["all_three_hold"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
