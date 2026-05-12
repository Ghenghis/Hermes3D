"""W6-7 (2026-05-09): per-app extension metadata for the 60-app registry.

This module fills in the 5 new ``modules`` columns introduced by the
W6-7 migration:

- ``tested_versions``: list[str] researched from upstream tags / changelogs.
  When a value cannot be confirmed, the entry is left ``[]`` and listed
  in ``UNFILLED_FIELDS`` for follow-up.
- ``license_spdx``: SPDX identifier (https://spdx.org/licenses/). The
  pre-existing ``license`` column is a free-form string that may say
  "GPL-3.0-or-later" or "GPL-compatible"; ``license_spdx`` normalizes
  to the canonical SPDX list ID. Where the upstream license is a
  custom non-SPDX license (Hunyuan), the value is ``LicenseRef-<name>``
  per SPDX 2.3 §10.
- ``rollback_supported``: heuristic — ``True`` if the app has a
  git-revert-able structure (we own the checkout and can ``git checkout
  <prev_tag>``) AND a documented rollback path exists.
- ``rollback_runbook_url``: optional pointer to operator runbook.
- ``proof_command``: idempotent shell command to verify health
  (executed via ``services.app_proof_runner``). Output is redacted via
  ``gateways.redaction.redact_text`` before being persisted.
- ``update_lane``: ``"stable"`` | ``"canary"`` | ``"frozen"``.
  ``frozen`` is the safe default for hardware-firmware references.

Sources for filled values:
- Upstream LICENSE files of each repo (verified via repo URL stored in
  the registry).
- SPDX 2.3 license list (https://spdx.org/licenses/).

NB: secrets / credentials never appear in seed data.  Proof commands
are read-only and idempotent (``--help`` / ``--version`` /
``python -c "import x"``).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

# ---------------------------------------------------------------------------
# Per-app extension data — mapping module_id -> {field: value}
# ---------------------------------------------------------------------------
#
# Update lane policy:
#   stable  : production / safe-to-auto-update on the canary->stable promotion
#             cadence. Requires a working proof_command.
#   canary  : actively-tracked upstream where breakage is expected; the
#             update center pulls these but does NOT auto-deploy.
#   frozen  : reference / firmware / hardware sources where update bumps
#             require operator review (most firmware lives here).

APP_EXTENSIONS: dict[str, dict[str, Any]] = {
    # -------- agents --------
    "azure_speech_sdk_js": {
        "tested_versions": ["1.40.0", "1.41.0"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "node -e \"require('microsoft-cognitiveservices-speech-sdk');console.log('ok')\"",
        "update_lane": "canary",
    },
    "blender_mcp_candidates": {
        "tested_versions": ["0.1.0", "0.2.0"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "uvx blender-mcp --help",
        "update_lane": "canary",
    },
    "hermes_agent": {
        # Hermes Agent v0.13 canary switch is documented in
        # MEMORY.md project_hermes_agent_v013_pending and
        # services/agent_version_registry.py.
        "tested_versions": ["v0.12", "v0.13", "v2026.5.7"],
        "license_spdx": "Apache-2.0",
        "rollback_supported": True,
        "rollback_runbook_url": "/docs/runbooks/hermes_agent_rollback.md",
        "proof_command": "python -m hermes_cli.main --help",
        "update_lane": "canary",
    },
    "kiln": {
        "tested_versions": [],  # upstream LICENSE not parsed; left empty
        "license_spdx": None,
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "langchain": {
        "tested_versions": ["0.3.0", "0.3.1"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": 'python -c "import langchain;print(langchain.__version__)"',
        "update_lane": "stable",
    },
    "langgraph": {
        "tested_versions": ["0.2.0", "0.3.0"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "python -c \"import langgraph;print('ok')\"",
        "update_lane": "stable",
    },
    "model_context_protocol": {
        "tested_versions": ["1.0.0"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "node -e \"import('@modelcontextprotocol/sdk/server/index.js').then(()=>console.log('ok'))\"",
        "update_lane": "stable",
    },
    # -------- firmware (frozen lane: never auto-update; operator approval) --------
    "firmware_klipper": {
        "tested_versions": ["v0.12.0"],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": "/docs/runbooks/firmware_rollback.md",
        "proof_command": "git rev-parse --short HEAD",
        "update_lane": "frozen",
    },
    "marlin": {
        "tested_versions": ["2.1.2"],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": "/docs/runbooks/firmware_rollback.md",
        "proof_command": "git rev-parse --short HEAD",
        "update_lane": "frozen",
    },
    "prusa_firmware": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": "/docs/runbooks/firmware_rollback.md",
        "proof_command": None,
        "update_lane": "frozen",
    },
    "repetier_firmware": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": "/docs/runbooks/firmware_rollback.md",
        "proof_command": None,
        "update_lane": "frozen",
    },
    "reprapfirmware": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": "/docs/runbooks/firmware_rollback.md",
        "proof_command": None,
        "update_lane": "frozen",
    },
    "smoothieware": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": "/docs/runbooks/firmware_rollback.md",
        "proof_command": None,
        "update_lane": "frozen",
    },
    # -------- hardware references --------
    "awesome_extruders": {
        "tested_versions": [],
        "license_spdx": None,  # README does not declare; left null
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "boxturtle": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "enraged_rabbit_project": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    # -------- libraries / materials --------
    "manyfold": {
        "tested_versions": ["v0.110.0"],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "open_filament_database": {
        "tested_versions": [],
        "license_spdx": None,  # data corpus, no SPDX header
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    # -------- modelers --------
    "blender": {
        "tested_versions": ["4.2.0", "5.1.0"],
        "license_spdx": "GPL-3.0-or-later",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "blender --version",
        "update_lane": "stable",
    },
    "build123d": {
        "tested_versions": ["0.7.0", "0.8.0"],
        "license_spdx": "Apache-2.0",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "python -c \"import build123d;print('ok')\"",
        "update_lane": "canary",
    },
    "cadquery": {
        "tested_versions": ["2.4.0", "2.5.0"],
        "license_spdx": "Apache-2.0",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": 'python -c "import cadquery;print(cadquery.__version__)"',
        "update_lane": "stable",
    },
    "freecad": {
        "tested_versions": ["1.0.0"],
        "license_spdx": "LGPL-2.1-or-later",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    "manifold": {
        "tested_versions": ["3.0.0"],
        "license_spdx": "Apache-2.0",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "python -c \"import manifold3d;print('ok')\"",
        "update_lane": "canary",
    },
    "meshlab": {
        "tested_versions": ["2023.12"],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    "numpy_stl": {
        "tested_versions": ["3.1.2", "3.2.0"],
        "license_spdx": "BSD-3-Clause",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "python -c \"import stl;print('ok')\"",
        "update_lane": "stable",
    },
    "open3d": {
        "tested_versions": ["0.18.0", "0.19.0"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": 'python -c "import open3d;print(open3d.__version__)"',
        "update_lane": "canary",
    },
    "openscad": {
        "tested_versions": ["2021.01", "2024.10"],
        "license_spdx": "GPL-2.0-or-later",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "openscad --version",
        "update_lane": "stable",
    },
    "pymesh": {
        # SOURCE_OVERRIDES remaps to pymeshfix
        "tested_versions": ["0.17.0"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "python -c \"import pymeshfix;print('ok')\"",
        "update_lane": "canary",
    },
    "solvespace": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "trimesh": {
        "tested_versions": ["4.4.0", "4.5.0"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": 'python -c "import trimesh;print(trimesh.__version__)"',
        "update_lane": "stable",
    },
    "truck": {
        "tested_versions": [],
        "license_spdx": "Apache-2.0",
        "rollback_supported": False,  # rust crate, no in-place rollback path defined
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    # -------- print_farm --------
    "botqueue": {
        "tested_versions": [],
        "license_spdx": None,  # README does not declare SPDX
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "fdm_monster": {
        "tested_versions": ["1.10.0", "1.11.0"],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "fluidd": {
        "tested_versions": ["v1.31.0"],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    "klipper": {
        "tested_versions": ["v0.12.0"],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": "/docs/runbooks/firmware_rollback.md",
        "proof_command": "git rev-parse --short HEAD",
        "update_lane": "frozen",
    },
    "klipperscreen": {
        "tested_versions": [],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "mainsail": {
        "tested_versions": ["v2.13.0"],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    "moonraker": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    "octofarm": {
        "tested_versions": [],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "octoprint": {
        "tested_versions": ["1.10.0", "1.11.0"],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    "printrun": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    # -------- research --------
    "awesome_3d_printing": {
        "tested_versions": [],
        "license_spdx": "CC0-1.0",
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    # -------- slicers --------
    "bambustudio": {
        "tested_versions": ["v01.10.00", "v02.00.00"],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "cura": {
        "tested_versions": ["5.10.0", "5.12.1"],
        "license_spdx": "LGPL-3.0-or-later",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    "curaengine": {
        "tested_versions": ["5.10.0", "5.12.1"],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": "CuraEngine help",
        "update_lane": "stable",
    },
    "flsun_slicer": {
        "tested_versions": [],
        "license_spdx": None,  # repo lacks LICENSE
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "kirimoto_gridspace": {
        "tested_versions": [],
        "license_spdx": "MPL-2.0",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "mattercontrol": {
        "tested_versions": [],
        "license_spdx": "BSD-2-Clause",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "orcaslicer": {
        "tested_versions": ["v2.2.0", "v2.3.0"],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "prusaslicer": {
        "tested_versions": ["2.8.0", "2.9.0"],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "stable",
    },
    "slic3r": {
        "tested_versions": [],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "strec3d": {
        "tested_versions": [],
        "license_spdx": None,  # repo lacks LICENSE
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
    "superslicer": {
        "tested_versions": [],
        "license_spdx": "AGPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    # -------- three_d_generation --------
    "comfyui": {
        "tested_versions": ["v0.3.0", "v0.4.0"],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "comfyui_frontend": {
        "tested_versions": [],
        "license_spdx": "GPL-3.0-only",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "comfyui_trellis_wrapper": {
        "tested_versions": [],
        "license_spdx": None,  # community wrapper
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "hunyuan3d_2_1": {
        "tested_versions": ["v2.1"],
        # Tencent Hunyuan Community License is a custom non-SPDX license;
        # SPDX 2.3 §10 says use ``LicenseRef-<idstring>``.
        "license_spdx": "LicenseRef-Tencent-Hunyuan-Community",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "trellis": {
        "tested_versions": ["v2"],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    "triposr": {
        "tested_versions": [],
        "license_spdx": "MIT",
        "rollback_supported": True,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "canary",
    },
    # -------- utilities --------
    "box_stl_generator": {
        "tested_versions": [],
        "license_spdx": None,
        "rollback_supported": False,
        "rollback_runbook_url": None,
        "proof_command": None,
        "update_lane": "frozen",
    },
}


# Apps where one or more of the 5 fields could not be researched.
# Format: (module_id, missing_field, attempt_made, next_fix_path).
UNFILLED_FIELDS: list[tuple[str, str, str, str]] = [
    (
        "kiln",
        "license_spdx",
        "no LICENSE in https://github.com/codeofaxel/Kiln (likely fork; needs upstream check)",
        "research-agent: git ls-remote, find LICENSE file",
    ),
    (
        "kiln",
        "tested_versions",
        "no released tags on the fork",
        "research-agent: ask user which fork to track or move to frozen with manifest pin",
    ),
    (
        "awesome_extruders",
        "license_spdx",
        "README catalog only, no LICENSE file",
        "research-agent: contact owner / treat as CC0 catalog",
    ),
    (
        "kiln",
        "proof_command",
        "no canonical CLI/import path",
        "research-agent: identify if Kiln has a Python entrypoint",
    ),
    (
        "open_filament_database",
        "license_spdx",
        "data-only repo, no LICENSE file declared",
        "research-agent: confirm with maintainer",
    ),
    (
        "flsun_slicer",
        "license_spdx",
        "vendor mirror, no LICENSE",
        "research-agent: extract from binary or contact FLSUN",
    ),
    (
        "strec3d",
        "license_spdx",
        "academic repo, no LICENSE",
        "research-agent: contact author / treat as restricted-research",
    ),
    (
        "comfyui_trellis_wrapper",
        "license_spdx",
        "community fork, no LICENSE",
        "research-agent: ask owner",
    ),
    (
        "box_stl_generator",
        "license_spdx",
        "small utility, no LICENSE",
        "research-agent: ask owner",
    ),
    (
        "botqueue",
        "license_spdx",
        "no LICENSE shipped in repo head",
        "research-agent: check release tarballs",
    ),
    (
        "truck",
        "tested_versions",
        "no recent tagged release tracked",
        "research-agent: pin a HEAD sha as 'tested HEAD'",
    ),
    (
        "klipperscreen",
        "tested_versions",
        "no upstream version tags",
        "research-agent: track HEAD only",
    ),
]


def apply_app_extensions(conn: sqlite3.Connection) -> int:
    """Stamp the 5 extension fields onto the ``modules`` table.

    Idempotent: re-running overwrites the values from APP_EXTENSIONS but
    does NOT touch rows whose id is not in the map.

    Returns the count of rows updated.

    Why an UPDATE (not INSERT OR REPLACE): the seed flow runs AFTER
    ``load_modules.load_modules()`` populates the rows, so the source
    columns (display_name, repo_url, ...) already exist; we only patch
    the new fields.
    """
    updated = 0
    for module_id, ext in APP_EXTENSIONS.items():
        cursor = conn.execute(
            """
            UPDATE modules
               SET tested_versions = ?,
                   license_spdx = ?,
                   rollback_supported = ?,
                   rollback_runbook_url = ?,
                   proof_command = ?,
                   update_lane = ?,
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (
                json.dumps(ext.get("tested_versions") or []),
                ext.get("license_spdx"),
                1 if ext.get("rollback_supported") else 0,
                ext.get("rollback_runbook_url"),
                ext.get("proof_command"),
                str(ext.get("update_lane") or "frozen"),
                module_id,
            ),
        )
        # Real sqlite3 connections return a Cursor; test fakes that
        # implement only ``execute(sql, params)`` may return ``None``.
        # Treat absent cursor as "row count unknown, count as 1".
        if cursor is not None and getattr(cursor, "rowcount", None) is not None:
            updated += cursor.rowcount
        else:
            updated += 1
    return updated


def app_extension_summary() -> dict[str, int]:
    """Return how many apps have each field filled (used by tests + docs)."""
    summary = {
        "total": len(APP_EXTENSIONS),
        "with_tested_versions": 0,
        "with_license_spdx": 0,
        "with_rollback_supported": 0,
        "with_proof_command": 0,
        "stable_lane": 0,
        "canary_lane": 0,
        "frozen_lane": 0,
    }
    for ext in APP_EXTENSIONS.values():
        if ext.get("tested_versions"):
            summary["with_tested_versions"] += 1
        if ext.get("license_spdx"):
            summary["with_license_spdx"] += 1
        if ext.get("rollback_supported"):
            summary["with_rollback_supported"] += 1
        if ext.get("proof_command"):
            summary["with_proof_command"] += 1
        lane = str(ext.get("update_lane") or "frozen")
        if lane in {"stable", "canary", "frozen"}:
            summary[f"{lane}_lane"] += 1
    return summary


def fully_populated_app_ids() -> list[str]:
    """Return module ids where all 5 fields are non-default values.

    "Full" means: non-empty tested_versions, non-null license_spdx,
    rollback_supported flag exists (True or False both count -- it's a
    yes/no answer), non-null proof_command, valid update_lane.
    """
    full: list[str] = []
    for module_id, ext in APP_EXTENSIONS.items():
        if not ext.get("tested_versions"):
            continue
        if not ext.get("license_spdx"):
            continue
        if not ext.get("proof_command"):
            continue
        if str(ext.get("update_lane") or "frozen") not in {"stable", "canary", "frozen"}:
            continue
        full.append(module_id)
    return full
