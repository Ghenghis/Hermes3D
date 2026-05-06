#!/usr/bin/env python3
"""Write a Source OS registry truth audit from the live loader state."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def add_src_to_path(repo_root: Path) -> None:
    src = repo_root / "03_implementation" / "src"
    sys.path.insert(0, str(src))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root_from_script())
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to 03_implementation/proof/SOURCE_REGISTRY_TRUTH_AUDIT.json.",
    )
    return parser.parse_args()


def is_git_checkout(path_value: str | None) -> bool:
    if not path_value:
        return False
    return (Path(path_value) / ".git").exists()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    add_src_to_path(repo_root)

    from hermes3d.db.init import connect, init_db
    from hermes3d.db.load_modules import load_modules

    init_db()
    loaded_count = load_modules()
    conn = connect()
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, display_name, section, priority, license, repo_url, local_path,
                   install_state, install_progress, detected_version, health, launch_kind
            FROM modules
            ORDER BY section, display_name
            """
        )
    ]
    conn.close()

    by_state = Counter(str(row["install_state"]) for row in rows)
    by_section = Counter(str(row["section"]) for row in rows)
    installed_git = [
        row
        for row in rows
        if row["install_state"] in {"installed", "healthy"} and is_git_checkout(row.get("local_path"))
    ]
    detected_non_git = [row for row in rows if row["install_state"] == "detected"]
    source_available = [row for row in rows if row["install_state"] == "source_available"]
    unavailable = [row for row in rows if row["install_state"] == "unavailable"]
    failed = [row for row in rows if row["install_state"] == "failed"]

    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "loader_entries": loaded_count,
            "registry_entries_unique": len(rows),
            "installed_git": len(installed_git),
            "detected_non_git": len(detected_non_git),
            "source_available_missing_checkout": len(source_available),
            "unavailable_no_verified_repo": len(unavailable),
            "failed_path": len(failed),
        },
        "by_state": dict(sorted(by_state.items())),
        "by_section": dict(sorted(by_section.items())),
        "not_operational": [
            {
                "id": row["id"],
                "display": row["display_name"],
                "section": row["section"],
                "repo": row["repo_url"],
                "local_path": row["local_path"],
                "state": row["install_state"],
                "health": row["health"],
                "reason": reason_for(row),
            }
            for row in [*source_available, *unavailable, *failed]
        ],
        "modules": rows,
    }

    out = args.out or repo_root / "03_implementation" / "proof" / "SOURCE_REGISTRY_TRUTH_AUDIT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


def reason_for(row: dict[str, Any]) -> str:
    state = row["install_state"]
    if state == "source_available":
        return "Real upstream repo is known, but no local checkout exists at the configured path."
    if state == "unavailable":
        return "No verified upstream repo or local checkout is configured."
    if state == "failed":
        return "Configured local source path exists but is not a usable directory."
    return "Not installed or not healthy."


if __name__ == "__main__":
    raise SystemExit(main())
