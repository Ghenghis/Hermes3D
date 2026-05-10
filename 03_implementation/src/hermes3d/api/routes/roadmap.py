from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from hermes3d.api.routes._common import rows

router = APIRouter()

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[4]
PROOF_DIR = IMPLEMENTATION_ROOT / "proof"
ACTION_PLAN_PATH = PROOF_DIR / "SOURCE_APP_RUNTIME_ACTION_PLAN.md"
COMPLETION_PATH = PROOF_DIR / "SOURCE_APP_60_COMPLETION_AUDIT.json"
CLI_READINESS_PATH = PROOF_DIR / "SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json"
CLI_SURFACE_PATH = PROOF_DIR / "SOURCE_APP_CLI_SURFACE_AUDIT.json"


@router.get("/api/roadmap/status")
def status() -> list[dict]:
    return rows("SELECT * FROM roadmap_items ORDER BY id")


@router.get("/api/roadmap/progress")
def progress() -> dict:
    items = status()
    return {
        "done": sum(1 for i in items if i["status"] == "DONE"),
        "in_progress": sum(1 for i in items if i["status"] == "IN_PROGRESS"),
        "not_started": sum(1 for i in items if i["status"] == "NOT_STARTED"),
        "total": len(items),
    }


@router.get("/api/roadmap/tab-completion")
def tab_completion() -> dict:
    source_truth = _source_runtime_truth()
    agent_operator_truth = _agent_operator_truth(source_truth)
    return {
        "updated_at": "2026-05-06",
        "roadmap_path": "03_implementation/ROADMAP.md",
        "source_runtime_action_plan": source_truth["action_plan"],
        "agent_operator_contract": agent_operator_truth,
        "contract": [
            "Visible controls must call a live local/API/backend path or expose an exact blocked reason.",
            "Use compact operator layouts that resize with the app window.",
            "Startup must select open localhost ports and publish the active UI/API URLs.",
            "FLSUN S1 remains read-only and printer-action locked until the user changes status.",
            "Hermes Agents may prepare work while idle, but risky actions remain proof-gated.",
            "Hermes Agents are not complete until every visible app, tab, button, and feature has an agent-callable action contract, safety policy, proof event, and exact ready or blocked state.",
        ],
        "tabs": [
            {
                "tab": "dashboard",
                "label": "Dashboard",
                "state": "done",
                "summary": "Live backend data, compact dashboard/simple mode, viewport proof recorded.",
            },
            {
                "tab": "simple",
                "label": "Simple GUI",
                "state": "done",
                "summary": "Selectable compact dashboard matching the user's preferred dense style.",
            },
            {
                "tab": "observe",
                "label": "Observe",
                "state": "done",
                "summary": "Live camera cards, S1 90-degree default, resize/undock/feed controls, backend plate policy.",
            },
            {
                "tab": "printers",
                "label": "Printers",
                "state": "done",
                "summary": "Correct T1/S1/V400 IP policy, S1 locked, guarded T1 print proof recorded.",
            },
            {
                "tab": "source_os",
                "label": "Source OS",
                "state": "in_progress",
                "summary": f"Source registry is resolved; Verify All, Setup Queue, selected-app Verify, and selected-app Setup Plan create proof; backup/update/rollback routes are UI-wired, {source_truth['runtime_ready']} verifier-backed rows are ready, {source_truth['verified_agent_cli']} real CLI probes are agent-usable, launch kinds are classified for all 60 rows, and safe setup runners remain for the remaining {source_truth['runner_gaps']} runner gaps.",
            },
            {
                "tab": "agents",
                "label": "Agents rail/chat",
                "state": "done",
                "summary": "Mic, voice-note upload, file attachments, quick context prompts, Azure reply voice playback, runtime SSE when configured, and bounded Playwright proof runs. Full OS operator coverage is tracked as a separate P0 gate.",
            },
            {
                "tab": "artifacts",
                "label": "Artifacts",
                "state": "done",
                "summary": "Agent attachments and proof files are inspectable through live artifacts API.",
            },
            {
                "tab": "settings",
                "label": "Settings",
                "state": "in_progress",
                "summary": "Hermes Agent/Desktop update failsafes exist; Environment shows runtime readiness plus source-app setup queue; app-wide update execution remains next.",
            },
            {
                "tab": "plugins",
                "label": "Plugins",
                "state": "in_progress",
                "summary": "Plugin state is live-backed and summarizes source update readiness plus the runtime setup queue; next gap is unified app release watch.",
            },
            {
                "tab": "jobs",
                "label": "Jobs",
                "state": "done",
                "summary": "Proof-gated pipeline renders backend transition state; cancel, repair proposal, repair apply/escalation, retry, and rollback routes append proof/job events and are UI-wired.",
            },
            {
                "tab": "autopilot",
                "label": "Autopilot",
                "state": "in_progress",
                "summary": "Guardrails/readiness routes exist; idle safe-work queue remains next.",
            },
            {
                "tab": "learning",
                "label": "Learning",
                "state": "in_progress",
                "summary": "Idle research config exists; daily review queue remains next.",
            },
            {
                "tab": "voice",
                "label": "Voice",
                "state": "in_progress",
                "summary": "Voice catalog/preview, chat mic, Azure STT, and agent reply voice playback are backend-wired; transcript review remains next.",
            },
            {
                "tab": "design",
                "label": "Design",
                "state": "in_progress",
                "summary": "P0 parametric desk-organizer executor is live with STL artifact, signed proof envelope, truth-gate row, and proof event; broader OpenSCAD/CadQuery/Blender coverage remains.",
            },
            {
                "tab": "gen3d",
                "label": "3D Generation",
                "state": "in_progress",
                "summary": "P0 calibration-cube generator is live with STL artifact, preview SVG, signed proof envelope, truth-gate row, and proof event; broader ComfyUI/TRELLIS.2/Hunyuan3D coverage remains.",
            },
            {
                "tab": "approvals",
                "label": "Approvals",
                "state": "done",
                "summary": "Pending/approved/rejected approval actions are live-backed.",
            },
            {
                "tab": "roadmap",
                "label": "Roadmap",
                "state": "in_progress",
                "summary": "This ledger is now exposed by live API and markdown.",
            },
        ],
        "next_packages": [
            {
                "id": "wp-agent-operator-coverage",
                "title": "Hermes Agents: Full OS Operator Coverage",
                "tabs": ["agents", "roadmap", "source_os", "settings"],
                "state": "active",
                "summary": agent_operator_truth["summary"],
                "acceptance": agent_operator_truth["acceptance"],
            },
            {
                "id": "wp-source-updates",
                "title": "Source OS + Plugins: App Update Center",
                "tabs": ["source_os", "plugins", "settings"],
                "state": "in_progress",
                "summary": f"Show installed version, runtime readiness, setup queue status, upstream latest release/commit, backup target, update button, rollback target, and proof gates for every source-backed app. Source OS, Plugins, Settings, and Roadmap now expose the corrected 60-app queue truth; `/api/modules/runtime/verifiers` exposes {source_truth['runtime_ready']} verifier-backed rows including {source_truth['verified_agent_cli']} agent-usable CLI probes, desktop metadata, read-only source inventory, package/import, and Moonraker/Klipper fleet probes; safe setup runners remain for the {source_truth['runner_gaps']} source-ready rows.",
                "acceptance": [
                    "No update action runs without backup metadata.",
                    "Failed or skipped gates stop or rollback.",
                    "Every app row shows runtime ready, source ready, install ready, setup needed, or exact blocked reason.",
                    "Setup Queue marks source-only apps as runner-not-registered until a safe module runner exists.",
                    "Keep the active Source OS count at the proven 60 rows; UI must not claim runtime readiness until a registered verifier row proves it.",
                    "If a source app offers a CLI, Hermes3D must prefer a bounded CLI verifier/runner for Hermes Agents; desktop launch metadata alone does not satisfy agent execution.",
                ],
            },
            {
                "id": "wp-fleet-onboarding",
                "title": "Printers + Settings: Fleet Onboarding",
                "tabs": ["printers", "settings"],
                "state": "next",
                "summary": "Add and validate new Moonraker/Klipper printers through Hermes Agents without manual config edits.",
                "acceptance": [
                    "New printer records IP, adapter, camera endpoint, safety state, and proof event.",
                    "Unavailable Moonraker endpoints show exact failed probe.",
                    "Existing T1/S1/V400 policy remains correct.",
                ],
            },
            {
                "id": "wp-job-pipeline",
                "title": "Jobs + Autopilot: Proof-Gated Job Pipeline",
                "tabs": ["jobs", "autopilot", "approvals"],
                "state": "next",
                "summary": "Show model, slice, bounds, approval, upload, print, observe, complete, repair stages with the current blocker and gate.",
                "acceptance": [
                    "Starting a print without job approval fails closed.",
                    "Every job transition appends proof.",
                    "Agent repair proposals require explicit approve/deny controls.",
                ],
            },
            {
                "id": "wp-idle-workbench",
                "title": "Learning + Agents: Idle Workbench",
                "tabs": ["learning", "agents", "roadmap"],
                "state": "next",
                "summary": "When idle, agents research safe improvements, app updates, source app opportunities, maintenance, and daily tasks for user review.",
                "acceptance": [
                    "Idle work never moves printers.",
                    "Idle work never merges or installs without proof and policy approval.",
                    "User gets a short daily queue with actionable choices.",
                ],
            },
            {
                "id": "wp-operator-assist",
                "title": "Voice + Observe: Operator Assist",
                "tabs": ["voice", "observe", "agents"],
                "state": "next",
                "summary": "Make voice and camera useful during prints by linking speech, snapshots, plate checks, and alerts to agent context.",
                "acceptance": [
                    "No speech key appears in frontend bundles or logs.",
                    "Voice transcription returns a real transcript or exact blocked reason.",
                    "Camera/plate alerts link to the exact printer card and proof event.",
                ],
            },
        ],
        "finish_queue": [
            {
                "priority": "P0",
                "title": "Design executor MVP",
                "state": "done",
                "summary": "Supported desk-organizer requests generate a real STL, proof envelope, job steps, artifacts, truth-gate row, and proof event. Unsupported prompts fail closed.",
            },
            {
                "priority": "P0",
                "title": "3D Generation executor and preview proof",
                "state": "done",
                "summary": "Supported calibration-cube requests generate a real STL, preview SVG, proof envelope, job steps, artifacts, truth-gate row, and proof event. Unsupported arbitrary prompts fail closed with provider setup guidance.",
            },
            {
                "priority": "P0",
                "title": "Jobs repair/rollback transitions",
                "state": "done",
                "summary": "Server-side cancel, repair proposal, repair apply/escalation, retry, and rollback endpoints append proof/job events and are reflected in Jobs. Rollback requires a recorded checkpoint artifact.",
            },
            {
                "priority": "P0",
                "title": "Source OS + Plugins update execution",
                "state": "partial",
                "summary": "Source OS Verify All, Setup Queue, selected-app Verify, selected-app Setup Plan, Backup, Check Update, Update, and Rollback controls now call backend routes with runtime/setup/backup/proof metadata; all-app release watch, safe setup runners, and richer smoke gates remain.",
            },
            {
                "priority": "P0",
                "title": "Hermes Agent full OS operator coverage",
                "state": "in_progress",
                "summary": agent_operator_truth["summary"],
            },
            {
                "priority": "P0",
                "title": "60 source-app runtime completion",
                "state": "in_progress",
                "summary": f"The active target is the proven 60 source-backed app rows. Current truth is {source_truth['runtime_ready']} verifier-backed ready rows, {source_truth['verified_agent_cli']} agent-usable CLI probes, and {source_truth['runner_gaps']} source-ready rows needing safe runner/verifier registration; launch-kind classification is 60/60 and no count expansion is active. The no-forget action plan tracks {source_truth['cli_candidates']} CLI/service signals needing verifier work.",
            },
            {
                "priority": "P1",
                "title": "Voice Azure STT pipeline",
                "state": "done",
                "summary": "Backend transcription reads Azure Speech secrets only from runtime/private env, returns transcript or exact blocker, and attaches proof to chat/artifacts.",
            },
            {
                "priority": "P1",
                "title": "Settings app update center",
                "state": "pending",
                "summary": "One-click check/update/rollback surface must cover Hermes Agent/Desktop and source apps with failsafes and user approval policy.",
            },
            {
                "priority": "P1",
                "title": "Printer onboarding/profile wizard polish",
                "state": "pending",
                "summary": "New printers need Moonraker probe, camera URL, profile refs, safety policy, and proof without editing TOML/source.",
            },
            {
                "priority": "P1",
                "title": "Idle automation workbench execution",
                "state": "pending",
                "summary": "Agents need to create research/build/update candidates while idle, run gates, and ask the user before install/merge.",
            },
            {
                "priority": "P1",
                "title": "Observe advanced view presets",
                "state": "done",
                "summary": "Camera selection layouts, 0/90/180/270 rotation, zoom/focus/color controls, undock, persisted presets, and refresh/reconnect proof are wired across the live Observe tab.",
            },
            {
                "priority": "P2",
                "title": "Final density/responsive pass",
                "state": "pending",
                "summary": "Every tab must use the available app window like the approved Simple/Agents layouts; dashboard stays non-scroll at operator viewport sizes.",
            },
            {
                "priority": "P2",
                "title": "Final docs/proof sync",
                "state": "pending",
                "summary": "README/roadmap/proof docs must match live tab count, printer policy, source app count, and current proof event IDs.",
            },
        ],
        "references": [
            {
                "label": "Moonraker Web API",
                "url": "https://moonraker.readthedocs.io/en/stable/web_api/",
            },
            {
                "label": "Moonraker update manager",
                "url": "https://moonraker.readthedocs.io/en/latest/external_api/update_manager/",
            },
            {
                "label": "Moonraker webcam config",
                "url": "https://moonraker.readthedocs.io/en/latest/configuration/#webcam",
            },
            {
                "label": "GitHub latest release REST API",
                "url": "https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#get-the-latest-release",
            },
            {
                "label": "PrusaSlicer CLI",
                "url": "https://github.com/prusa3d/PrusaSlicer/wiki/Command-Line-Interface",
            },
            {
                "label": "OpenSCAD CLI",
                "url": "https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_OpenSCAD_in_a_command_line_environment",
            },
            {"label": "OrcaSlicer source", "url": "https://github.com/OrcaSlicer/OrcaSlicer"},
        ],
    }


def _source_runtime_truth() -> dict:
    completion = _read_json(COMPLETION_PATH)
    cli_readiness = _read_json(CLI_READINESS_PATH)
    cli_surface = _read_json(CLI_SURFACE_PATH)
    counts = completion.get("runtime_setup_queue", {}).get("counts", {})
    readiness_summary = cli_readiness.get("summary", {})
    surface_summary = cli_surface.get("summary", {})
    runner_gaps = int(
        counts.get("runner_not_registered") or readiness_summary.get("runner_gaps") or 0
    )
    runtime_ready = int(counts.get("runtime_ready") or 0)
    verified_agent_cli = int(
        readiness_summary.get("verified_agent_cli") or surface_summary.get("agent_enabled_cli") or 0
    )
    cli_candidates = int(surface_summary.get("candidate_needs_verifier") or 0)
    generated_at = (
        completion.get("generated_at_utc")
        or cli_readiness.get("generated_at_utc")
        or cli_surface.get("generated_at_utc")
    )
    return {
        "runtime_ready": runtime_ready,
        "runner_gaps": runner_gaps,
        "verified_agent_cli": verified_agent_cli,
        "cli_candidates": cli_candidates,
        "action_plan": {
            "path": "03_implementation/proof/SOURCE_APP_RUNTIME_ACTION_PLAN.md",
            "exists": ACTION_PLAN_PATH.is_file(),
            "generated_at_utc": generated_at,
            "source_backed_apps": int(completion.get("target", {}).get("source_backed_apps") or 60),
            "runtime_ready": runtime_ready,
            "runner_gaps": runner_gaps,
            "verified_agent_cli": verified_agent_cli,
            "cli_candidates": cli_candidates,
            "rule": "No Source OS row becomes Hermes Agent usable until a bounded verifier and proof gate pass.",
        },
    }


def _agent_operator_truth(source_truth: dict) -> dict:
    runner_gaps = int(source_truth.get("runner_gaps") or 0)
    verified_agent_cli = int(source_truth.get("verified_agent_cli") or 0)
    cli_candidates = int(source_truth.get("cli_candidates") or 0)
    missing = [
        f"Register safe verifier/runner contracts for the remaining {runner_gaps} Source OS rows before agents can execute those apps.",
        f"Promote the {cli_candidates} CLI/service signals into bounded agent runners with smoke gates, or mark each one with an exact blocked reason.",
        "Complete the Settings/Source OS one-click app update center: backup, check, update, smoke gate, rollback, and approval policy for every app family.",
        "Add an agent action catalog for every tab action so agents call the same backend route as the UI instead of relying on ad hoc chat instructions.",
        "Expand generation/modeling provider coverage beyond the current bounded local templates before arbitrary prompt-to-model work is considered agent-operable.",
        "Keep risky idle work blocked until live blockers, pending approvals, and proof gates are clear.",
    ]
    return {
        "state": "in_progress",
        "summary": (
            "Hermes Agent chat/runtime is ready, but full OS operator coverage is not complete. "
            f"Agents currently have {verified_agent_cli} verified Source OS CLI runners plus chat, attachments, voice, idle research reports, and Playwright proof runs; "
            f"{runner_gaps} source-app runner gaps and the app update center remain before agents can operate every offered Hermes3D OS action end to end."
        ),
        "ready_now": [
            "Chat/SSE bridge to the configured local/private Hermes Agent runtime.",
            "Browser mic, audio/model/file attachments, Azure reply voice, and artifact proof rows.",
            "Bounded Playwright observe/smoke/full proof runs with artifacts and proof events.",
            "Idle research report execution when runtime is ready; risky idle work stays proof-gated.",
            "Read-only Observe/printer telemetry and policy-gated printer actions through backend routes.",
            f"{verified_agent_cli} verified Source OS CLI runners exposed through backend verifier proof.",
        ],
        "missing": missing,
        "blocked_now": [
            "FLSUN S1 remains read-only/action locked by user policy.",
            "Queued or active jobs block risky idle build/update/merge/printer work until the system is quiet.",
        ],
        "acceptance": [
            "Every visible UI action has a backend action route or exact blocked reason.",
            "Every backend action route is callable by Hermes Agents through a registered action contract.",
            "Every action contract declares safety policy, required approval, proof event, and rollback or no-rollback reason.",
            "Every Source OS app with CLI/API/import/service capability has a bounded verifier/runner before agents can mark it usable.",
            "Every app update path has backup, smoke gate, rollback, and user approval policy.",
            "Printer actions keep S1 locked and enforce print approval/truth gates before upload/start/move/test.",
        ],
    }


def _read_json(path: Path) -> dict:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
