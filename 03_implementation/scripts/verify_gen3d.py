"""Source + runtime verifier for Hermes3D generative-3D providers.

Lane H3D-CLAUDE-SOURCE-GEN3D. Verifies five providers --
ComfyUI, TRELLIS, Hunyuan3D, TripoSR, Bambu Studio -- without performing
any heavy operation. Strict no-download rules:

* Repo reachability is probed with ``git ls-remote --heads`` (no clone).
* Python entrypoint is probed with ``pip show <pkg>`` (no install).
* Model-weight readiness is reported as a boolean for known cache dirs only.
* Bambu Studio is a desktop app; verifier checks the launcher path's
  presence on disk (no launch).

Outputs proof at:
    03_implementation/proof/GEN3D_VERIFY_2026-05-06.json

Exits 0 even if individual probes fail -- "honest not installed" is the
correct answer; the proof JSON encodes the per-provider truth.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = IMPLEMENTATION_ROOT / "adapter_registry" / "schemas"
PROOF_DIR = IMPLEMENTATION_ROOT / "proof"
PROOF_PATH = PROOF_DIR / "GEN3D_VERIFY_2026-05-06.json"

PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "comfyui",
        "schema": "comfyui.schema.json",
        "label": "ComfyUI",
        "kind": "python_runtime",
    },
    {
        "id": "trellis2",
        "schema": "trellis2.schema.json",
        "label": "TRELLIS",
        "kind": "python_runtime",
    },
    {
        "id": "hunyuan3d",
        "schema": "hunyuan3d.schema.json",
        "label": "Hunyuan3D",
        "kind": "python_runtime",
    },
    {
        "id": "triposr",
        "schema": "triposr.schema.json",
        "label": "TripoSR",
        "kind": "python_runtime",
    },
    {
        "id": "bambustudio_bridge",
        "schema": "bambustudio_bridge.schema.json",
        "label": "Bambu Studio",
        "kind": "desktop_app",
    },
]

GIT_LS_REMOTE_TIMEOUT_S = 5
PIP_SHOW_TIMEOUT_S = 5


def main() -> int:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    git_path = shutil.which("git")
    pip_cmd = _resolve_pip_command()
    results: list[dict[str, Any]] = []
    for provider in PROVIDERS:
        results.append(verify_provider(provider, git_path=git_path, pip_cmd=pip_cmd))
    proof = {
        "$schema": "hermes3d://proof/gen3d_verify_v1",
        "lane": "H3D-CLAUDE-SOURCE-GEN3D",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_platform": sys.platform,
        "git_available": bool(git_path),
        "pip_command": pip_cmd,
        "policy": {
            "downloads": "forbidden",
            "git": "ls-remote only (no clone)",
            "pip": "show only (no install)",
            "weights": "boolean cache presence only (no fetch)",
            "desktop_apps": "executable presence only (no launch)",
        },
        "providers": results,
        "summary": _summarize(results),
    }
    PROOF_PATH.write_text(json.dumps(proof, indent=2, sort_keys=True), encoding="utf-8")
    print(str(PROOF_PATH))
    print(json.dumps(proof["summary"], indent=2, sort_keys=True))
    return 0


def verify_provider(
    provider: dict[str, Any],
    *,
    git_path: str | None,
    pip_cmd: list[str] | None,
) -> dict[str, Any]:
    schema_path = SCHEMAS_DIR / str(provider["schema"])
    schema = _load_schema(schema_path)
    defaults = _schema_defaults(schema)
    source_repo = defaults.get("source_repo")
    pip_package = defaults.get("pip_package")
    weights_cache_dirs = list(defaults.get("weights_cache_dirs") or [])
    executable_path = defaults.get("executable_path")
    repo_probe = probe_git_ls_remote(source_repo, git_path=git_path)
    pip_probe = probe_pip_show(pip_package, pip_cmd=pip_cmd)
    weights = probe_weights_cache(weights_cache_dirs)
    executable = probe_executable_presence(executable_path)
    installed = bool(pip_probe.get("installed")) or bool(executable.get("present"))
    return {
        "id": provider["id"],
        "label": provider["label"],
        "kind": provider["kind"],
        "schema_path": str(schema_path.relative_to(IMPLEMENTATION_ROOT)),
        "schema_valid": schema is not None,
        "source_repo": source_repo,
        "pip_package": pip_package,
        "weights_cache_dirs": weights_cache_dirs,
        "executable_path": executable_path,
        "repo_reachable": repo_probe,
        "pip_show": pip_probe,
        "weights_present": weights,
        "executable_present": executable,
        "installed": installed,
        "proof_gate_version": "gen3d-source-runtime-verifier-v1",
    }


def probe_git_ls_remote(repo: str | None, *, git_path: str | None) -> dict[str, Any]:
    if not repo:
        return {"reachable": False, "reason": "no source_repo declared"}
    if not git_path:
        return {"reachable": False, "reason": "git not on PATH"}
    cmd = [git_path, "ls-remote", "--heads", repo]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=GIT_LS_REMOTE_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"reachable": False, "reason": "timeout", "timeout_s": GIT_LS_REMOTE_TIMEOUT_S}
    except OSError as exc:
        return {"reachable": False, "reason": f"OSError: {type(exc).__name__}"}
    refs = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    return {
        "reachable": proc.returncode == 0 and bool(refs),
        "return_code": proc.returncode,
        "ref_count": len(refs),
        "first_ref": refs[0][:200] if refs else None,
        "stderr_head": _head_lines(proc.stderr or ""),
    }


def probe_pip_show(package: str | None, *, pip_cmd: list[str] | None) -> dict[str, Any]:
    if not package:
        return {"installed": False, "reason": "no pip_package declared"}
    if not pip_cmd:
        return {"installed": False, "reason": "no pip command available"}
    cmd = [*pip_cmd, "show", package]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PIP_SHOW_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"installed": False, "reason": "timeout", "timeout_s": PIP_SHOW_TIMEOUT_S}
    except OSError as exc:
        return {"installed": False, "reason": f"OSError: {type(exc).__name__}"}
    output = proc.stdout or ""
    version: str | None = None
    location: str | None = None
    for line in output.splitlines():
        if line.lower().startswith("version:"):
            version = line.split(":", 1)[1].strip()
        elif line.lower().startswith("location:"):
            location = line.split(":", 1)[1].strip()
    return {
        "installed": proc.returncode == 0 and bool(version),
        "return_code": proc.returncode,
        "version": version,
        "location": location,
    }


def probe_weights_cache(paths: list[str]) -> dict[str, Any]:
    expanded: list[dict[str, Any]] = []
    for raw in paths:
        if not raw:
            continue
        path = Path(os.path.expanduser(os.path.expandvars(raw)))
        expanded.append(
            {
                "configured": raw,
                "resolved": str(path),
                "exists": path.exists(),
                "is_dir": path.is_dir(),
            }
        )
    any_present = any(item["exists"] for item in expanded)
    return {
        "any_present": any_present,
        "checked": expanded,
    }


def probe_executable_presence(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {"present": False, "reason": "no executable_path declared"}
    path = Path(path_value)
    return {
        "configured": path_value,
        "resolved": str(path),
        "present": path.is_file(),
    }


def _resolve_pip_command() -> list[str] | None:
    candidates: list[list[str]] = [[sys.executable, "-m", "pip"]]
    pip_path = shutil.which("pip")
    if pip_path:
        candidates.append([pip_path])
    for cmd in candidates:
        try:
            proc = subprocess.run(
                [*cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=PIP_SHOW_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            return cmd
    return None


def _load_schema(schema_path: Path) -> dict[str, Any] | None:
    if not schema_path.is_file():
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _schema_defaults(schema: dict[str, Any] | None) -> dict[str, Any]:
    if not schema:
        return {}
    properties = schema.get("properties") or {}
    out: dict[str, Any] = {}
    for key, prop in properties.items():
        if isinstance(prop, dict) and "default" in prop:
            out[key] = prop["default"]
    return out


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    installed = [r["id"] for r in results if r.get("installed")]
    repo_ok = [r["id"] for r in results if (r.get("repo_reachable") or {}).get("reachable")]
    weights_ok = [r["id"] for r in results if (r.get("weights_present") or {}).get("any_present")]
    return {
        "total": len(results),
        "installed": installed,
        "not_installed": [r["id"] for r in results if not r.get("installed")],
        "repo_reachable": repo_ok,
        "weights_present": weights_ok,
    }


def _head_lines(value: str, *, max_lines: int = 6, max_chars: int = 240) -> list[str]:
    lines = value.splitlines()
    return [
        line if len(line) <= max_chars else f"{line[:max_chars]}..." for line in lines[:max_lines]
    ]


if __name__ == "__main__":
    raise SystemExit(main())
