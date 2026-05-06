"""Initialize and seed the Hermes3D GUI SQLite database."""

from __future__ import annotations

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "var" / "hermes3d.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _migrate(conn)
    _seed(conn)
    conn.commit()
    conn.close()
    return DB_PATH


def _migrate(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(onboarded_printers)").fetchall()}
    if "ip" not in columns:
        conn.execute("ALTER TABLE onboarded_printers ADD COLUMN ip TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_onboarded_printers_ip ON onboarded_printers(ip)")


def _seed(conn: sqlite3.Connection) -> None:
    _seed_roadmap(conn)
    _seed_plugins(conn)
    _seed_voice_assignments(conn)
    _seed_settings(conn)
    _seed_module_runtime_verifiers(conn)
    _seed_module_providers(conn)


def _seed_roadmap(conn: sqlite3.Connection) -> None:
    items = [
        (1, "Moonraker fleet (T1-A, T1-B, V400) connected and live", "printers", None),
        (2, "FLSUN S1 safety lock cleared and movement verified", "printers", None),
        (3, "PrusaSlicer or OrcaSlicer installed and profile locked", "source_os", "slicers"),
        (4, "CadQuery Worker running and proof verified", "source_os", "modelers"),
        (5, "Local Modeling LLM active and reachable", "plugins", None),
        (6, "TRELLIS.2 or Hunyuan3D-2.1 generation engine active", "plugins", None),
        (7, "ComfyUI running with Hermes workflow loaded", "source_os", "three_d_generation"),
        (8, "Autopilot readiness: all 16 checks READY", "autopilot", None),
        (9, "First guarded job created and evidence attached", "jobs", None),
        (10, "First real print job approved and dispatched", "approvals", None),
        (11, "Evidence Ledger recording all gate events", "plugins", None),
        (12, "Idle Learning Mode running first research cycle", "learning", None),
        (13, "All 20 plugins at ACTIVE or READY state", "plugins", None),
        (14, "Source OS app update center with backup and rollback gates", "source_os", "updates"),
        (15, "Fleet onboarding wizard for new Moonraker printers", "printers", "onboarding"),
        (16, "Jobs/Autopilot proof-gated repair pipeline", "jobs", "proof_pipeline"),
        (17, "Idle Hermes Agent workbench with daily user review queue", "learning", "idle_queue"),
        (18, "Voice and Observe operator assist linked to live camera proof", "voice", "operator_assist"),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO roadmap_items (id, description, link_tab, link_section)
        VALUES (?, ?, ?, ?)
        """,
        items,
    )


def _seed_plugins(conn: sqlite3.Connection) -> None:
    plugins = [
        ("moonraker", "Moonraker", "Moonraker API adapter for Klipper printers", "ACTIVE"),
        ("autopilot-setup", "Autopilot Setup", "Readiness and safe-action orchestrator", "ACTIVE"),
        ("camera-observer", "Camera Observer", "Camera feed and observation plugin", "READY"),
        ("prusaslicer", "PrusaSlicer", "PrusaSlicer CLI integration", "PLANNED"),
        ("orcaslicer", "OrcaSlicer", "OrcaSlicer CLI integration", "PLANNED"),
        ("cadquery", "CadQuery", "Parametric CAD worker", "PLANNED"),
        ("openscad", "OpenSCAD", "Script-based CAD worker", "PLANNED"),
        ("trellis2", "TRELLIS.2", "Image-to-3D generation engine", "PLANNED"),
        ("hunyuan3d", "Hunyuan3D-2.1", "Hunyuan3D generation engine", "PLANNED"),
        ("triposr", "TripoSR", "Fast 3D reconstruction engine", "PLANNED"),
        ("blender-trimesh", "Blender/Trimesh", "Mesh processing workers", "PLANNED"),
        ("azure-voice", "Azure Voice", "Azure TTS/STT bridge", "ACTIVE"),
        ("minimax-mcp-vision", "MiniMax-MCP Vision", "Vision analysis plugin", "ACTIVE"),
        ("deepseek-v4", "DeepSeek V4", "Language model integration", "READY"),
        ("visual-evidence", "Visual Evidence", "Evidence capture and attachment", "ACTIVE"),
        ("local-modeling-llm", "Local Modeling LLM", "Local modeling LLM", "PLANNED"),
        ("fdm-monster", "FDM Monster", "Print farm management", "PLANNED"),
        ("maintenance", "Maintenance", "Printer maintenance tracking", "ACTIVE"),
        ("filament", "Filament", "Filament profile management", "PLANNED"),
        ("evidence-ledger", "Evidence Ledger", "Immutable proof ledger", "ACTIVE"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO plugins (id, name, description, state) VALUES (?, ?, ?, ?)",
        plugins,
    )


def _seed_voice_assignments(conn: sqlite3.Connection) -> None:
    assignments = [
        ("factory-operator", "Factory Operator", "en-US-JennyNeural", "azure"),
        ("modeling-agent", "Modeling Agent", "en-US-GuyNeural", "azure"),
        ("print-safety-agent", "Print Safety Agent", "en-US-AriaNeural", "azure"),
        ("mesh-go-agent", "Mesh Go Agent", "en-US-DavisNeural", "azure"),
        ("mesh-repair-agent", "Mesh Repair Agent", "en-US-JasonNeural", "azure"),
        ("oliver-qa-agent", "Oliver QA Agent", "en-US-TonyNeural", "azure"),
        ("print-monitor-agent", "Print Monitor Agent", "en-US-NancyNeural", "azure"),
        ("privacy-agent", "Privacy Agent", "en-US-SaraNeural", "azure"),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO voice_assignments
            (agent_id, agent_name, voice_name, provider)
        VALUES (?, ?, ?, ?)
        """,
        assignments,
    )


def _seed_settings(conn: sqlite3.Connection) -> None:
    settings = [
        ("theme", "midnight"),
        ("ports.api", "7862"),
        ("ports.web", "5173"),
        ("ports.camera_proxy", "8080"),
        ("ports.telemetry", "9090"),
        ("ports.model_llm", "11434"),
        ("ports.cadquery_worker", "9001"),
        ("ports.openscad_worker", "9002"),
        ("ports.slicer_worker", "9003"),
    ]
    conn.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", settings)


def _seed_module_runtime_verifiers(conn: sqlite3.Connection) -> None:
    from hermes3d.services.module_runtime import BUILTIN_RUNTIME_PROBES

    records = [
        (
            module_id,
            str(probe.get("label") or module_id),
            str(probe.get("kind") or "cli"),
            probe.get("tool_key"),
            probe.get("path"),
            json.dumps(list(probe.get("args") or [])),
            json.dumps(list(probe.get("capabilities") or [])),
            1 if probe.get("execute") else 0,
            int(probe.get("timeout_s") or 12),
            1,
            str(probe.get("proof_gate_version") or "runtime-verifier-v1"),
            str(probe.get("notes") or "Seeded safe non-destructive runtime verifier."),
        )
        for module_id, probe in sorted(BUILTIN_RUNTIME_PROBES.items())
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO module_runtime_verifiers
            (module_id, label, runner_kind, tool_key, executable_path, args,
             capabilities, execute, timeout_s, enabled, proof_gate_version, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )


def _seed_module_providers(conn: sqlite3.Connection) -> None:
    providers = [
        (
            "official_blender",
            "blender_mcp_candidates",
            "Official Blender Connector",
            "blender_mcp",
            "https://www.blender.org/",
            "Install from Claude Desktop connector directory; Blender 4.2+ add-on",
            '["Claude Desktop connector install", "Blender side-panel Connect to Claude"]',
            '["read_scene", "execute_blender_python", "batch_scene_cleanup", "modifier_node_inspection"]',
            "GPL-compatible",
            "available",
            "Built by Blender developers for Claude; best default for direct Blender Python/API work.",
        ),
        (
            "ahujasid",
            "blender_mcp_candidates",
            "Blender MCP ahujasid",
            "blender_mcp",
            "https://github.com/ahujasid/blender-mcp",
            "uvx blender-mcp",
            '["uvx blender-mcp --help", "claude mcp list"]',
            '["get_scene_info", "get_viewport_screenshot", "execute_blender_code", "export_3mf"]',
            "MIT",
            "available",
            "Original open-source MCP bridge; useful as the free/community fallback.",
        ),
        (
            "vxai",
            "blender_mcp_candidates",
            "Blender MCP VxAI",
            "blender_mcp",
            "https://github.com/VxASI/blender-mcp-vxai",
            "manual provider install after validation",
            '["claude mcp list"]',
            '["get_scene_info", "get_viewport_screenshot", "execute_blender_code"]',
            "MIT",
            "available",
            "Community fork for direct agent scene construction and iterative natural-language control.",
        ),
        (
            "csm",
            "blender_mcp_candidates",
            "Common Sense Machines Blender MCP",
            "blender_mcp",
            "https://github.com/CommonSenseMachines/blender-mcp",
            "install per CSM repository instructions",
            '["provider-specific CSM validation"]',
            '["text_to_4d", "csm_api_bridge", "animated_asset_workflow"]',
            "MIT",
            "available",
            "Specialized CSM.ai bridge for text/image-to-4D and animated asset workflows.",
        ),
        (
            "3d_agent",
            "blender_mcp_candidates",
            "3D-Agent",
            "blender_mcp",
            "https://3d-agent.com/blender-mcp",
            "Install 3D-Agent Blender add-on",
            '["3D-Agent add-on installed", "provider connection validated"]',
            '["text_to_3d", "clean_topology", "export_obj", "export_fbx", "export_glb", "export_usdz"]',
            "mixed-free-tier",
            "external",
            "Production-oriented add-on path; switchable but not claimed open-source until user installs and validates terms.",
        ),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO module_providers
            (id, module_id, display_name, provider_kind, repo_url, install_command,
             verify_commands, capabilities, license, state, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        providers,
    )
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('source_os.blender_mcp.active_provider', 'official_blender')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('source_os.blender_mcp_candidates.active_provider', 'official_blender')"
    )


if __name__ == "__main__":
    print(f"Database initialized at {init_db()}")
