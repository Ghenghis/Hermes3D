#!/usr/bin/env python3
"""Validate Hermes3D external_repos_registry.yaml for execution readiness."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:
    print(f"ERROR: PyYAML is required: {exc}", file=sys.stderr)
    sys.exit(2)

REQUIRED_TOP_KEYS = {"name", "type", "required", "version_policy", "install", "verify", "adapter", "os_support"}
REQUIRED_INSTALL_KEYS = {"method"}
REQUIRED_VERIFY_KEYS = {"commands", "expected"}
REQUIRED_ADAPTER_KEYS = {"mode", "capabilities"}

def validate_tool(tool_id: str, item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_TOP_KEYS - set(item)
    if missing:
        errors.append(f"{tool_id}: missing keys {sorted(missing)}")
    if not (item.get("repo") or item.get("source") or item.get("homepage")):
        errors.append(f"{tool_id}: must include repo, source, or homepage")
    install = item.get("install") or {}
    if not isinstance(install, dict):
        errors.append(f"{tool_id}: install must be object")
    elif REQUIRED_INSTALL_KEYS - set(install):
        errors.append(f"{tool_id}: install missing {sorted(REQUIRED_INSTALL_KEYS - set(install))}")
    verify = item.get("verify") or {}
    if not isinstance(verify, dict):
        errors.append(f"{tool_id}: verify must be object")
    else:
        miss = REQUIRED_VERIFY_KEYS - set(verify)
        if miss:
            errors.append(f"{tool_id}: verify missing {sorted(miss)}")
        if not verify.get("commands"):
            errors.append(f"{tool_id}: verify.commands cannot be empty")
    adapter = item.get("adapter") or {}
    if not isinstance(adapter, dict):
        errors.append(f"{tool_id}: adapter must be object")
    else:
        miss = REQUIRED_ADAPTER_KEYS - set(adapter)
        if miss:
            errors.append(f"{tool_id}: adapter missing {sorted(miss)}")
    version_policy = item.get("version_policy") or {}
    if not isinstance(version_policy, dict):
        errors.append(f"{tool_id}: version_policy must be object")
    elif not any(k in version_policy for k in ("pin", "channel", "manual_select", "locked")):
        errors.append(f"{tool_id}: version_policy needs pin/channel/manual_select/locked")
    return errors

def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config/external_repos_registry.yaml")
    if not path.exists():
        print(f"ERROR: registry not found: {path}", file=sys.stderr); return 1
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tools = data.get("tools") if isinstance(data, dict) and "tools" in data else data
    if not isinstance(tools, dict) or not tools:
        print("ERROR: registry must contain non-empty tools object", file=sys.stderr); return 1
    errors: list[str] = []
    for tool_id, item in tools.items():
        if not isinstance(item, dict):
            errors.append(f"{tool_id}: entry must be object")
        else:
            errors.extend(validate_tool(str(tool_id), item))
    if errors:
        print("Registry validation FAILED")
        for error in errors: print(f"- {error}")
        return 1
    print(f"Registry validation PASS: {len(tools)} tools checked")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
