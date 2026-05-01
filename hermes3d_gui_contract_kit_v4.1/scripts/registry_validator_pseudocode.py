"""DEPRECATED — see the production validator under src/hermes3d/registry/.

This file used to contain a pseudocode validator that referenced an obsolete
schema (`repositories` / `display_name` / `repo_url`) which never matched the
real registry (`tools` / `name` / `repo`). It was misleading reference material
and was replaced in Phase 1.

The real implementation lives at:

    03_implementation/src/hermes3d/registry/validator.py

Run it via the package CLI:

    python -m hermes3d.registry.validator [PATH-TO-REGISTRY-YAML]

or use the wrapper scripts at the repo root:

    bash scripts/validate-registry.sh
    pwsh scripts/validate-registry.ps1

The kit also still ships a minimal baseline validator at
`hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py` for use by
implementers who only have the kit checked out (no src tree).
"""
import sys

_MSG = (
    "registry_validator_pseudocode.py is deprecated. "
    "Use: python -m hermes3d.registry.validator <path-to-registry-yaml>"
)

if __name__ == "__main__":
    sys.stderr.write(_MSG + "\n")
    sys.exit(2)
