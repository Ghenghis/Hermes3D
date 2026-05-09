"""Load Source OS modules from the external repository registry."""

from __future__ import annotations

import json
import os
import re
import subprocess
from contextlib import closing
from pathlib import Path
from typing import Any

from hermes3d.db.init import DB_PATH, connect, init_db
from hermes3d.services.agent_checkout import hermes_agent_checkout as _hermes_agent_checkout_at_import

REFERENCE_LAUNCH_KINDS = {
    "catalog_reference",
    "firmware_source",
    "hardware_reference",
    "reference",
    "rust_library_reference",
    "service_reference",
    "source_reference",
    "touch_ui_reference",
    "web_app_reference",
}
IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_ROOT = Path(
    os.environ.get(
        "HERMES3D_SOURCE_ROOT",
        str(IMPLEMENTATION_ROOT / "source-lab" / "sources"),
    )
)
SOURCE_REGISTRY_PROOF_PATH = IMPLEMENTATION_ROOT / "proof" / "SOURCE_REGISTRY_TRUTH_AUDIT.json"
SOURCE_MANIFEST_CANDIDATES = [
    Path(os.environ["HERMES3D_SOURCE_MANIFEST"]) if os.environ.get("HERMES3D_SOURCE_MANIFEST") else None,
    IMPLEMENTATION_ROOT / "source-lab" / "source_manifest.json",
    Path("G:/Github/Hermes3D-OS/source-lab/source_manifest.json"),
]
SECTION_TARGET_DIRS = {
    "slicers": "slicers",
    "modelers": "modelers",
    "print_farm": "print-farm",
    "firmware": "firmware",
    "three_d_generation": "generation",
    "agents": "orchestration",
    "library": "libraries",
    "materials": "materials",
    "hardware": "hardware",
    "utilities": "utilities",
    "research": "research",
}
MANIFEST_ID_ALIASES = {
    "strec3d": "strecs3d",
}
SOURCE_OVERRIDES = {
    # The registry intentionally kept these as candidates/policies; the contract
    # kit later pinned the truthful source mapping.
    "pymesh": {
        "repo": "https://github.com/pyvista/pymeshfix.git",
        "local_path": str(DEFAULT_SOURCE_ROOT / "modelers" / "pymeshfix"),
    },
    "blender_mcp_candidates": {
        "repo": "https://github.com/ahujasid/blender-mcp.git",
        "local_path": str(DEFAULT_SOURCE_ROOT / "orchestration" / "blender-mcp"),
    },
    "flsun_slicer": {
        "repo": "https://github.com/Flsun3d/FlsunSlicer.git",
        "local_path": "G:/Github/Hermes3D-OS/source-lab/sources/slicers/FLSUN-Slicer",
    },
    "printrun": {
        "repo": "https://github.com/kliment/Printrun.git",
        "local_path": "G:/Github/Hermes3D-OS/source-lab/sources/print-farm/Printrun",
    },
    # Link the user's existing checked-out agent source instead of claiming a
    # missing source-lab copy. Hermes Agent v0.13 canary switch
    # (Wave A4 finding): use ``hermes_agent_checkout()`` so an operator
    # can flip canary↔production via ``HERMES_AGENT_CHECKOUT`` env var.
    # Note: this dict is built at module import; canary requires the env
    # var be set BEFORE process start for this site (the HTTP route
    # ``_repo_path()`` reads env per-call and supports mid-process flip).
    "hermes_agent": {
        "repo": "https://github.com/NousResearch/Hermes-Agent.git",
        "local_path": str(_hermes_agent_checkout_at_import()),
    },
}
LAUNCH_KIND_OVERRIDES = {
    "bambustudio": "desktop_or_cli",
    "mattercontrol": "desktop_app",
    "slic3r": "desktop_or_cli",
    "strec3d": "desktop_app",
    "superslicer": "desktop_or_cli",
    "firmware_klipper": "service",
    "marlin": "firmware_source",
    "prusa_firmware": "firmware_source",
    "reprapfirmware": "firmware_source",
    "repetier_firmware": "firmware_source",
    "smoothieware": "firmware_source",
    "awesome_extruders": "catalog_reference",
    "boxturtle": "hardware_reference",
    "enraged_rabbit_project": "hardware_reference",
    "blender_mcp_candidates": "python_worker",
    "kiln": "web_app_reference",
    "langchain": "source_reference",
    "langgraph": "source_reference",
    "model_context_protocol": "npm_package",
}


def _registry_path() -> Path:
    """Return the loader-real registry YAML path.

    Bonus 12 finding #9 fix (PR #135 / synthesis 2026-05-09):
    ``Path(__file__).resolve().parents[5]`` is evaluated unguarded. On a
    frozen build / zipapp / nuitka package, ``__file__`` may be much
    shallower than 5 directories from any plausible repo root, raising
    ``IndexError`` BEFORE the ``FileNotFoundError`` fallback to
    ``_registry_from_committed_proof`` can trigger. Wrap each candidate
    expression in its own try/except so a malformed candidate is dropped,
    not propagated.
    """
    candidates: list[Path] = [
        Path("G:/Github/Hermes3D/Hermes3D-GUI-Wiring-Contract-Kit/03_REPO_REGISTRY/external_repos_registry.yaml"),
    ]
    try:
        candidates.append(
            Path(__file__).resolve().parents[5]
            / "Hermes3D-GUI-Wiring-Contract-Kit"
            / "03_REPO_REGISTRY"
            / "external_repos_registry.yaml"
        )
    except IndexError:
        # Frozen build / zipapp: __file__ is shallower than parents[5];
        # silently skip this candidate so the FileNotFoundError fallback
        # to _registry_from_committed_proof can still fire.
        pass
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("external_repos_registry.yaml was not found")


def _registry_from_committed_proof(path: Path = SOURCE_REGISTRY_PROOF_PATH) -> dict[str, dict[str, dict[str, Any]]]:
    if not path.exists():
        raise FileNotFoundError("external_repos_registry.yaml was not found and SOURCE_REGISTRY_TRUTH_AUDIT.json is absent")
    proof = json.loads(path.read_text(encoding="utf-8"))
    modules = proof.get("modules")
    if not isinstance(modules, list) or not modules:
        raise ValueError("SOURCE_REGISTRY_TRUTH_AUDIT.json does not contain a non-empty modules list")
    data: dict[str, dict[str, dict[str, Any]]] = {}
    for module in modules:
        if not isinstance(module, dict):
            continue
        module_id = str(module.get("id") or "").strip()
        section = str(module.get("section") or "").strip()
        if not module_id or not section:
            continue
        data.setdefault(section, {})[module_id] = {
            "display": module.get("display_name") or module_id,
            "priority": module.get("priority") or "reference",
            "license": module.get("license"),
            "repo": module.get("repo_url"),
            "launch_kind": module.get("launch_kind") or "unknown",
            "bridge_tasks": [],
        }
    if not data:
        raise ValueError("SOURCE_REGISTRY_TRUTH_AUDIT.json did not yield registry module rows")
    return data


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    return value


def _parse_registry(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    data: dict[str, dict[str, dict[str, Any]]] = {}
    current_section: str | None = None
    current_module: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0 and line.endswith(":"):
            current_section = line[:-1]
            data[current_section] = {}
            current_module = None
        elif indent == 2 and line.endswith(":") and current_section:
            current_module = line[:-1]
            data[current_section][current_module] = {}
        elif indent >= 4 and ":" in line and current_section and current_module:
            key, value = line.split(":", 1)
            data[current_section][current_module][key.strip()] = _parse_scalar(value)
    return data


def _safe_path_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return name or "source"


def _match_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _repo_key(value: Any) -> str:
    repo = str(value or "").strip().lower()
    if repo.endswith(".git"):
        repo = repo[:-4]
    return repo.rstrip("/")


def _source_manifest_path() -> Path | None:
    for candidate in SOURCE_MANIFEST_CANDIDATES:
        if candidate and candidate.exists():
            return candidate
    return None


def _manifest_source_root(path: Path, manifest: dict[str, Any]) -> Path:
    raw_root = Path(str(manifest.get("sourceRoot") or "source-lab/sources"))
    if raw_root.is_absolute():
        return raw_root
    repo_root = path.parent.parent
    return repo_root / raw_root


def _manifest_index() -> dict[str, dict[str, Any]]:
    path = _source_manifest_path()
    if not path:
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    source_root = _manifest_source_root(path, manifest)
    index: dict[str, dict[str, Any]] = {}
    for entries in manifest.get("groups", {}).values():
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            enriched = dict(entry)
            target = enriched.get("target")
            if target:
                enriched["local_path"] = str(source_root / str(target))
            for key in (
                _match_key(enriched.get("id")),
                _match_key(enriched.get("name")),
                _repo_key(enriched.get("repo")),
            ):
                if key:
                    index[key] = enriched
    return index


def _match_manifest_entry(module_id: str, entry: dict[str, Any], manifest: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    aliased_module_id = MANIFEST_ID_ALIASES.get(module_id, module_id)
    keys = [
        _match_key(module_id),
        _match_key(aliased_module_id),
        _match_key(entry.get("display")),
        _repo_key(entry.get("repo")),
    ]
    for key in keys:
        if key and key in manifest:
            return manifest[key]
    return None


def resolve_module_source(
    section_key: str,
    module_id: str,
    entry: dict[str, Any],
    manifest: dict[str, dict[str, Any]] | None = None,
) -> dict[str, str | None]:
    manifest_entry = _match_manifest_entry(module_id, entry, manifest or _manifest_index())
    override = SOURCE_OVERRIDES.get(module_id, {})
    repo_url = override.get("repo") or (manifest_entry or {}).get("repo") or entry.get("repo")
    local_path = override.get("local_path") or (manifest_entry or {}).get("local_path")
    if not local_path and repo_url:
        section_dir = SECTION_TARGET_DIRS.get(section_key, _safe_path_name(section_key))
        display = str(entry.get("display") or module_id)
        local_path = str(DEFAULT_SOURCE_ROOT / section_dir / _safe_path_name(display))
    return {
        "repo_url": str(repo_url) if repo_url else None,
        "local_path": str(local_path) if local_path else None,
    }


def _git_version(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    version = proc.stdout.strip()
    return version or None


def inspect_source_path(local_path: str | None, repo_url: str | None) -> dict[str, Any]:
    if not local_path:
        return {
            "install_state": "source_available" if repo_url else "unavailable",
            "install_progress": 0,
            "detected_version": None,
            "health": "unknown",
        }
    path = Path(local_path)
    if not path.exists():
        return {
            "install_state": "source_available" if repo_url else "unavailable",
            "install_progress": 0,
            "detected_version": None,
            "health": "unknown",
        }
    if not path.is_dir():
        return {
            "install_state": "failed",
            "install_progress": 0,
            "detected_version": None,
            "health": "failed",
        }
    version = _git_version(path)
    if version:
        return {
            "install_state": "installed",
            "install_progress": 100,
            "detected_version": version,
            "health": "unknown",
        }
    return {
        "install_state": "detected",
        "install_progress": 100,
        "detected_version": None,
        "health": "degraded",
    }


def load_modules() -> int:
    """Load the external-repos registry into the SQLite ``modules`` table.

    Bonus 12 finding #10 fix (PR #135 / synthesis 2026-05-09):
    The pre-fix function used a bare ``conn = connect(); ...; conn.commit();
    conn.close()`` with no ``try/finally`` and no rollback. A ``KeyError``
    or ``sqlite3.IntegrityError`` mid-loop (e.g. a non-string value the
    parameterized INSERT rejects) raised out of the loop with the
    connection still open, leaking the FD and the WAL files on Windows.

    Post-fix: ``with closing(conn) as conn:`` always closes the connection;
    a try/except around the loop runs ``conn.rollback()`` on any exception
    before re-raising, so partial loads do NOT leave half-committed state.
    """
    if not DB_PATH.exists():
        init_db()
    try:
        registry = _parse_registry(_registry_path())
    except FileNotFoundError:
        registry = _registry_from_committed_proof()
    manifest = _manifest_index()
    count = 0
    seen_ids: set[str] = set()
    with closing(connect()) as conn:
        try:
            for section_key, entries in registry.items():
                for module_id, entry in entries.items():
                    unique_id = module_id if module_id not in seen_ids else f"{section_key}_{module_id}"
                    seen_ids.add(unique_id)
                    launch_kind = LAUNCH_KIND_OVERRIDES.get(unique_id) or LAUNCH_KIND_OVERRIDES.get(module_id) or entry.get("launch_kind") or "unknown"
                    source = resolve_module_source(section_key, module_id, entry, manifest)
                    source_status = inspect_source_path(source["local_path"], source["repo_url"])
                    install_state = source_status["install_state"]
                    if not source["repo_url"] and launch_kind in REFERENCE_LAUNCH_KINDS:
                        install_state = "unavailable"
                    tasks = entry.get("required_actions") or entry.get("bridge_tasks") or []
                    if isinstance(tasks, str):
                        tasks = [tasks]
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO modules
                            (id, display_name, section, priority, license, repo_url, local_path,
                             install_state, install_progress, detected_version, health, launch_kind,
                             bridge_tasks, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (
                            unique_id,
                            entry.get("display", module_id),
                            section_key,
                            entry.get("priority", "reference"),
                            entry.get("license"),
                            source["repo_url"],
                            source["local_path"],
                            install_state,
                            source_status["install_progress"],
                            source_status["detected_version"],
                            source_status["health"],
                            launch_kind,
                            json.dumps(tasks),
                        ),
                    )
                    for task_name in tasks:
                        task_id = f"{unique_id}::{task_name}"
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO bridge_tasks (id, module_id, name, status)
                            VALUES (?, ?, ?, 'pending')
                            """,
                            (task_id, unique_id, str(task_name)),
                        )
                    count += 1
            conn.commit()
        except Exception:
            # Bonus 12 #10: roll back partial inserts so the next caller
            # does not see a half-loaded modules table. Re-raise so
            # operators see the real failure.
            try:
                conn.rollback()
            except Exception:  # nosec - best-effort during teardown
                pass
            raise
    return count


if __name__ == "__main__":
    print(f"Loaded {load_modules()} modules from registry.")
