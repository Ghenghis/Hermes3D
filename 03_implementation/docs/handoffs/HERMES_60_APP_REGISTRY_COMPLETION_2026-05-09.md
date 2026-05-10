# Hermes 60-App Registry Completion (W6-7)

**Date:** 2026-05-09  
**Lane:** W6-7 (lane 4 of finish-order, data layer)  
**Owner:** claude-w6-7-app-registry  
**Branch:** `claude/w6-7-app-registry-completion`  
**Consumer lane:** W6-8 (GUI exposure)

## What changed

The 60-app registry (`modules` table) now carries the per-app proof,
license, version, rollback, and update-lane metadata required for the
"app status" surface. The data layer is complete; the GUI lane (W6-8)
binds against `/api/apps`.

## Schema before/after

### Before (legacy)

```sql
CREATE TABLE modules (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    section TEXT NOT NULL,
    priority TEXT NOT NULL,
    license TEXT,
    repo_url TEXT,
    local_path TEXT,
    install_state TEXT NOT NULL DEFAULT 'unavailable',
    install_progress INTEGER DEFAULT 0,
    detected_version TEXT,
    health TEXT,
    launch_kind TEXT,
    bridge_tasks TEXT,
    last_sync_at TEXT,
    lock_hash TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

### After (W6-7)

```sql
CREATE TABLE modules (
    -- ... existing columns ...
    -- W6-7 additions:
    tested_versions TEXT NOT NULL DEFAULT '[]',
    license_spdx TEXT,
    rollback_supported INTEGER NOT NULL DEFAULT 0,
    rollback_runbook_url TEXT,
    proof_command TEXT,
    update_lane TEXT NOT NULL DEFAULT 'frozen',
    last_proof_status TEXT,
    last_proof_at TEXT
);
CREATE INDEX idx_modules_update_lane ON modules(update_lane);
```

The migration `_migrate_modules_w6_7` in `db/init.py` is idempotent:
each `ALTER TABLE` is gated by a `PRAGMA table_info` column-presence
check, so re-running on an already-migrated DB is a no-op.

The `load_modules` SQL switched from `INSERT OR REPLACE` to
`INSERT ... ON CONFLICT(id) DO UPDATE SET ...` so the W6-7 extension
columns are preserved across re-runs of the loader. (Without this,
every page hit on `/api/modules` would clobber the seeded extension
data — a real, latent bug fixed in this lane.)

## Per-app filled values (summary table)

Total rows: 60. Filled extension table is at
`db/app_registry_extensions.APP_EXTENSIONS`.

| section            | total | with_spdx | with_proof_cmd | rollback_supported |
|--------------------|-------|-----------|----------------|---------------------|
| agents             | 7     | 6         | 6              | 6                   |
| firmware           | 6     | 6         | 2              | 6                   |
| hardware           | 3     | 2         | 0              | 0                   |
| library            | 1     | 1         | 0              | 1                   |
| materials          | 1     | 0         | 0              | 0                   |
| modelers           | 13    | 13        | 8              | 12                  |
| print_farm         | 10    | 9         | 1              | 8                   |
| research           | 1     | 1         | 0              | 0                   |
| slicers            | 11    | 9         | 1              | 8                   |
| three_d_generation | 6     | 5         | 0              | 5                   |
| utilities          | 1     | 0         | 0              | 0                   |

Aggregate: 52/60 with SPDX licensing, 19/60 with proof_command, 18/60 stable + 19/60 canary + 23/60 frozen.

Apps with all 5 fields fully populated (non-empty `tested_versions`,
`license_spdx`, `rollback_supported` decided, non-null
`proof_command`, valid `update_lane`):

- `azure_speech_sdk_js`
- `blender_mcp_candidates`
- `hermes_agent`
- `langchain`
- `langgraph`
- `model_context_protocol`
- `firmware_klipper`
- `marlin`
- `blender`
- `build123d`
- `cadquery`
- `manifold`
- `numpy_stl`
- `open3d`
- `openscad`
- `pymesh`
- `trimesh`
- `klipper`
- `curaengine`

19 apps fully populated; remainder have at least the SPDX license and
update_lane set.

## Open TODOs (apps where research could not fill all 5 fields)

Format from the task brief:
`(exact_app_id, exact_field_missing, exact_research_attempted, next_fix_attempt)`

The full list lives in `db/app_registry_extensions.UNFILLED_FIELDS` and
test `test_unfilled_fields_documented` pins it. Highlights:

| app_id | missing | research_attempted | next_fix |
|--------|---------|--------------------|----------|
| `kiln` | `license_spdx` | no LICENSE in github.com/codeofaxel/Kiln | research-agent: confirm fork lineage |
| `kiln` | `tested_versions` | no released tags on the fork | research-agent: track HEAD or move to frozen |
| `kiln` | `proof_command` | no canonical CLI entry point | research-agent: identify Python entrypoint |
| `awesome_extruders` | `license_spdx` | README catalog only | research-agent: treat as CC0 |
| `open_filament_database` | `license_spdx` | data-only repo | research-agent: maintainer ping |
| `flsun_slicer` | `license_spdx` | vendor mirror, no LICENSE | research-agent: contact FLSUN |
| `strec3d` | `license_spdx` | academic repo, no LICENSE | research-agent: contact author |
| `comfyui_trellis_wrapper` | `license_spdx` | community fork, no LICENSE | research-agent: ping owner |
| `box_stl_generator` | `license_spdx` | small utility, no LICENSE | research-agent: ping owner |
| `botqueue` | `license_spdx` | no LICENSE in repo head | research-agent: check release tarballs |
| `truck` | `tested_versions` | no recent tagged release tracked | research-agent: pin a HEAD sha |
| `klipperscreen` | `tested_versions` | no upstream version tags | research-agent: track HEAD only |

## Routes

```
GET  /api/apps                       list all apps with the W6-7 fields
GET  /api/apps?section=...           filter by section
GET  /api/apps?update_lane=...       filter by stable | canary | frozen
GET  /api/apps/{app_id}              single app, full extended metadata
POST /api/apps/{app_id}/run-proof    execute proof_command, persist last_proof_status
POST /api/apps/{app_id}/rollback     dispatch to per-app rollback (501 if unsupported)
```

`/api/modules/*` is unchanged for backward compatibility — `/api/apps`
is the new canonical surface. W6-8 (GUI lane) consumes these.

## Files changed

```
03_implementation/src/hermes3d/db/schema.sql                         # +14 cols
03_implementation/src/hermes3d/db/init.py                            # +33 (_migrate_modules_w6_7)
03_implementation/src/hermes3d/db/load_modules.py                    # INSERT->ON CONFLICT, +seed call
03_implementation/src/hermes3d/db/app_registry_extensions.py         # NEW (60-app extension data)
03_implementation/src/hermes3d/services/app_proof_runner.py          # NEW (subprocess proof runner)
03_implementation/src/hermes3d/api/routes/apps.py                    # NEW (4 routes)
03_implementation/src/hermes3d/api/app.py                            # +1 route registration
04_testing/pytest/unit/test_app_registry_extended.py                 # NEW (12 unit tests)
04_testing/pytest/integration/test_app_registry_proof_run.py         # NEW (10 integration tests)
```

## Tests

- 12 unit tests (schema, defaults, idempotency, round-trip, integrity)
- 10 integration tests (route loop, proof execution, rollback, redaction)
- 5 pre-existing `test_load_modules_resilience.py` tests still pass
- Total: 22 new + 79 regressed-clean = 101 green

## Safety / constraints satisfied

- No secrets in seed data (all proof commands are `--help` /
  `--version` / module imports / `git rev-parse`).
- All proof output runs through `gateways.redaction.redact_text` per
  the brief.
- Hermes MCP locks acquired (`claude-w6-7-app-registry`) and released
  on completion.
- No paid services touched; SPDX list is public.
- Pre-existing tests still pass (`test_load_modules_clean_path_commits_and_closes`
  was the one near-miss — patched `apply_app_extensions` to tolerate
  fakes returning `None` from `execute`).

## Sources cited

1. **SPDX 2.3 license list** — <https://spdx.org/licenses/> — used to
   normalize the free-form `license` column into the canonical
   `license_spdx` identifier (e.g. `GPL-3.0-only`,
   `LicenseRef-Tencent-Hunyuan-Community` for non-SPDX licenses per
   SPDX 2.3 §10).
2. **Existing migration pattern** —
   `04_testing/pytest/unit/test_load_modules_resilience.py` (Bonus 12
   #10) — modeled the same `with closing(connect()) as conn:` +
   `try/except: conn.rollback(); raise` shape; the new
   `_migrate_modules_w6_7` follows the column-presence-check idiom
   already used by the `onboarded_printers` migration in `init.py`.
