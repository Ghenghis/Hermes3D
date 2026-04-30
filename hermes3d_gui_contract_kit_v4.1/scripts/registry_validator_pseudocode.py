"""Pseudocode for Claude to implement in Hermes3D.
Validates config/external_repos_registry.yaml.
"""
from pathlib import Path
import yaml

REQUIRED_FIELDS = ["display_name", "role", "adapter"]

def validate_registry(path: str) -> list[str]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    errors = []
    repos = data.get("repositories", {})
    if not repos:
        errors.append("No repositories declared")
    for key, item in repos.items():
        for field in REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{key}: missing {field}")
        if "repo_url" not in item and "local_user_archives" not in item:
            errors.append(f"{key}: missing repo_url or local_user_archives")
    return errors
