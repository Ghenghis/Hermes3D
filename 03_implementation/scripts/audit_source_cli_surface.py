from __future__ import annotations

import json
import re
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = IMPLEMENTATION_ROOT / "proof" / "SOURCE_APP_CLI_SURFACE_AUDIT.json"

CLI_PREFERRED_LAUNCH_KINDS = {"cli_worker", "cli_or_python_worker", "desktop_or_cli"}
CLI_POSSIBLE_LAUNCH_KINDS = {
    "desktop_app",
    "python_worker",
    "gpu_worker",
    "service",
    "web_app",
    "npm_package",
}
AGENT_CLI_VERIFIER_KINDS = {"cli", "python_module_cli"}
ROOT_DOC_NAMES = ("README.md", "README.rst", "README.txt", "readme.md", "readme.rst")
ROOT_CONFIG_NAMES = (
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Makefile",
    "makefile",
    "Cargo.toml",
)
README_SIGNAL_RE = re.compile(
    r"(?i)\b(command[- ]line|cli|usage:\s*\S+|python\s+-m|npm\s+run|pnpm\s+run|yarn\s+run|uv\s+run|console_scripts?)\b"
)


def main() -> int:
    import sys

    sys.path.insert(0, str(IMPLEMENTATION_ROOT / "src"))
    from hermes3d.db.init import connect, init_db
    from hermes3d.db.load_modules import load_modules
    from hermes3d.services.module_runtime import module_runtime_probe

    init_db()
    load_modules()
    conn = connect()
    try:
        modules = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, display_name, section, launch_kind, install_state, local_path, repo_url
                  FROM modules
                 ORDER BY section, display_name
                """
            ).fetchall()
        ]
    finally:
        conn.close()

    records = []
    for module in modules:
        runtime = module_runtime_probe(module, live=False)
        records.append(classify_cli_surface(module, runtime))

    counts = Counter(record["cli_surface_status"] for record in records)
    enabled = [record["module_id"] for record in records if record["agent_enabled"]]
    candidates = [
        record["module_id"]
        for record in records
        if record["cli_surface_status"].endswith("_needs_verifier")
    ]
    audit = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "target": {
            "source_backed_apps": len(records),
            "rule": "Hermes Agents may use CLI/service runners only after a bounded local verifier proves the runtime. CLI hints in source docs are candidates, not enabled actions.",
            "s1_policy": "Camera/read-only only; no printer action runners are enabled for S1.",
        },
        "summary": {
            "by_cli_surface_status": dict(sorted(counts.items())),
            "agent_enabled_cli": len(enabled),
            "agent_enabled_cli_modules": enabled,
            "candidate_needs_verifier": len(candidates),
            "candidate_needs_verifier_modules": candidates,
            "no_local_cli_signal": sum(
                1 for record in records if record["cli_surface_status"] == "no_local_cli_signal"
            ),
        },
        "records": records,
        "next_actions": [
            "Keep verified agent CLIs exposed through bounded help/version/dry-run runners first.",
            "Promote candidate CLI surfaces only by adding a module_runtime_verifier row and proof gate.",
            "Do not mark package scripts, README commands, or desktop launchers agent-ready without a live non-destructive verifier.",
            "For service/web apps, prove a local health endpoint before exposing Start/Stop/Bridge controls.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"path": str(OUTPUT), **audit["summary"]}, indent=2, sort_keys=True))
    return 0


def classify_cli_surface(module: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    local_path = Path(str(module.get("local_path") or ""))
    launch_kind = str(module.get("launch_kind") or "unknown")
    runtime_status = str(runtime.get("status") or "blocked")
    verifier_kind = str(runtime.get("kind") or launch_kind)
    proof_gate = str(runtime.get("proof_gate_version") or "")
    agent_tier = agent_execution_tier(module, runtime)
    source_signals = inspect_source_signals(local_path)

    if agent_tier == "verified_agent_cli":
        surface_status = "enabled_agent_cli"
        next_action = "Keep bounded Hermes Agent CLI runner enabled and add dry-run task smoke before mutating files."
        agent_enabled = True
    elif agent_tier == "launcher_metadata_only":
        surface_status = "launcher_only_not_cli"
        next_action = (
            "Keep as launcher metadata only until a safe CLI/API/desktop-bridge smoke is proven."
        )
        agent_enabled = False
    elif any(
        signal["kind"] in {"package_bin", "python_console_script", "root_executable"}
        for signal in source_signals
    ):
        surface_status = "cli_candidate_needs_verifier"
        next_action = "Add a non-destructive CLI verifier before exposing this to Hermes Agents."
        agent_enabled = False
    elif any(signal["kind"] in {"package_script", "make_target"} for signal in source_signals):
        surface_status = "service_or_setup_candidate_needs_verifier"
        next_action = (
            "Add a health/version/setup verifier before exposing service or setup actions."
        )
        agent_enabled = False
    elif agent_tier in {"source_reference_ready", "package_or_import_ready", "service_api_ready"}:
        surface_status = f"{agent_tier}_not_cli"
        next_action = (
            "Use the existing proof tier; add a separate runner smoke before any write actions."
        )
        agent_enabled = False
    elif any(signal["kind"] == "readme_cli_signal" for signal in source_signals):
        surface_status = "documentation_cli_signal_needs_verifier"
        next_action = "Confirm the documented command in the local runtime and register a verifier."
        agent_enabled = False
    else:
        surface_status = "no_local_cli_signal"
        next_action = "Keep agent actions disabled until local docs/source reveal a safe runner or the app is installed."
        agent_enabled = False

    return {
        "module_id": str(module.get("id") or ""),
        "display": str(module.get("display_name") or module.get("id") or ""),
        "section": str(module.get("section") or ""),
        "launch_kind": launch_kind,
        "install_state": str(module.get("install_state") or ""),
        "agent_execution_tier": agent_tier,
        "cli_surface_status": surface_status,
        "agent_enabled": agent_enabled,
        "runtime_status": runtime_status,
        "verifier": runtime.get("verifier"),
        "verifier_kind": verifier_kind,
        "proof_gate_version": proof_gate,
        "path": str(runtime.get("path") or module.get("local_path") or ""),
        "source_signals": source_signals[:12],
        "next_action": next_action,
    }


def agent_execution_tier(module: dict[str, Any], runtime: dict[str, Any]) -> str:
    runtime_status = str(runtime.get("status") or "blocked")
    kind = str(runtime.get("kind") or module.get("launch_kind") or "unknown")
    proof_gate = str(runtime.get("proof_gate_version") or "")
    launch_kind = str(module.get("launch_kind") or "unknown")
    executed = bool(runtime.get("executed"))
    if runtime_status == "ready" and kind in AGENT_CLI_VERIFIER_KINDS and executed:
        return "verified_agent_cli"
    if runtime_status == "ready" and (
        proof_gate == "desktop-launcher-metadata-v1" or (kind == "desktop_app" and not executed)
    ):
        return "launcher_metadata_only"
    if runtime_status == "ready" and kind in {
        "python_import",
        "python_source_import",
        "node_package",
    }:
        return "package_or_import_ready"
    if runtime_status == "ready" and kind in {"local_http_health", "moonraker_fleet"}:
        return "service_api_ready"
    if runtime_status == "ready" and kind == "source_inventory":
        return "source_reference_ready"
    if launch_kind in CLI_PREFERRED_LAUNCH_KINDS:
        return "cli_preferred_gap"
    if launch_kind in CLI_POSSIBLE_LAUNCH_KINDS:
        return f"{launch_kind}_gap"
    return "runner_gap"


def inspect_source_signals(path: Path) -> list[dict[str, str]]:
    if not path.is_dir():
        return []
    signals: list[dict[str, str]] = []
    signals.extend(package_json_signals(path / "package.json"))
    signals.extend(pyproject_signals(path / "pyproject.toml"))
    signals.extend(setup_py_signals(path / "setup.py"))
    signals.extend(makefile_signals(path / "Makefile"))
    signals.extend(makefile_signals(path / "makefile"))
    signals.extend(root_executable_signals(path))
    signals.extend(readme_signals(path))
    return signals


def package_json_signals(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        pkg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    signals: list[dict[str, str]] = []
    bin_value = pkg.get("bin")
    if isinstance(bin_value, str):
        signals.append(
            {
                "kind": "package_bin",
                "source": "package.json",
                "name": str(pkg.get("name") or "bin"),
                "command": bin_value,
            }
        )
    elif isinstance(bin_value, dict):
        for name, command in list(bin_value.items())[:8]:
            signals.append(
                {
                    "kind": "package_bin",
                    "source": "package.json",
                    "name": str(name),
                    "command": str(command),
                }
            )
    scripts = pkg.get("scripts")
    if isinstance(scripts, dict):
        for name, command in scripts.items():
            lname = str(name).lower()
            if lname in {"start", "serve", "dev", "cli"} or "cli" in lname or "server" in lname:
                signals.append(
                    {
                        "kind": "package_script",
                        "source": "package.json",
                        "name": str(name),
                        "command": str(command)[:220],
                    }
                )
    return signals[:12]


def pyproject_signals(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    signals: list[dict[str, str]] = []
    project = data.get("project") if isinstance(data, dict) else None
    if isinstance(project, dict):
        scripts = project.get("scripts")
        if isinstance(scripts, dict):
            for name, target in list(scripts.items())[:12]:
                signals.append(
                    {
                        "kind": "python_console_script",
                        "source": "pyproject.toml",
                        "name": str(name),
                        "command": str(target),
                    }
                )
    poetry = data.get("tool", {}).get("poetry") if isinstance(data.get("tool"), dict) else None
    if isinstance(poetry, dict):
        scripts = poetry.get("scripts")
        if isinstance(scripts, dict):
            for name, target in list(scripts.items())[:12]:
                signals.append(
                    {
                        "kind": "python_console_script",
                        "source": "pyproject.toml",
                        "name": str(name),
                        "command": str(target),
                    }
                )
    return signals


def setup_py_signals(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if "console_scripts" not in text:
        return []
    matches = re.findall(r"['\"]([^'\"]+=\s*[^'\"]+)['\"]", text)
    return [
        {
            "kind": "python_console_script",
            "source": "setup.py",
            "name": item.split("=", 1)[0].strip(),
            "command": item.strip()[:220],
        }
        for item in matches[:12]
    ] or [
        {
            "kind": "python_console_script",
            "source": "setup.py",
            "name": "console_scripts",
            "command": "console_scripts declared",
        }
    ]


def makefile_signals(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    signals: list[dict[str, str]] = []
    for line in lines[:300]:
        if not line or line.startswith(("\t", " ", "#")):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)\s*:", line)
        if match and match.group(1).lower() in {"run", "serve", "start", "cli", "dev", "server"}:
            signals.append(
                {
                    "kind": "make_target",
                    "source": path.name,
                    "name": match.group(1),
                    "command": f"make {match.group(1)}",
                }
            )
    return signals[:8]


def root_executable_signals(path: Path) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    try:
        children = list(path.iterdir())
    except OSError:
        return signals
    for child in sorted(children, key=lambda item: item.name.lower()):
        if child.is_file() and child.suffix.lower() in {".exe", ".cmd", ".bat", ".ps1"}:
            signals.append(
                {
                    "kind": "root_executable",
                    "source": "root",
                    "name": child.name,
                    "command": str(child),
                }
            )
    return signals[:8]


def readme_signals(path: Path) -> list[dict[str, str]]:
    readme = next((path / name for name in ROOT_DOC_NAMES if (path / name).is_file()), None)
    if not readme:
        return []
    try:
        lines = readme.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    signals: list[dict[str, str]] = []
    for line in lines[:500]:
        cleaned = " ".join(line.strip().split())
        if cleaned and README_SIGNAL_RE.search(cleaned):
            signals.append(
                {
                    "kind": "readme_cli_signal",
                    "source": readme.name,
                    "name": "docs",
                    "command": cleaned[:220],
                }
            )
        if len(signals) >= 8:
            break
    return signals


if __name__ == "__main__":
    raise SystemExit(main())
