"""Truth labels for Source OS app proof coverage.

The app registry has two different "not ready" meanings that used to be
flattened into ``NO_PROOF_COMMAND``:

* reference/catalog rows that are intentionally read-only and should not be
  sold as runnable apps, and
* runnable/service/modeling rows that still need a safe verifier contract.

This module keeps that distinction in one place so /api/apps and
/api/source-os/modules agree.
"""

from __future__ import annotations

from typing import Any


def classify_app_proof(record: dict[str, Any]) -> dict[str, str | None]:
    """Return explicit proof truth metadata for a registry row."""
    proof_command = str(record.get("proof_command") or "").strip()
    if proof_command:
        return {
            "proof_capability": "COMMAND_PROOF",
            "proof_capability_label": "Command proof available",
            "proof_gap_reason": None,
            "proof_next_action": "Run the seeded proof command to refresh pass/fail evidence.",
        }

    section = str(record.get("section") or "").strip()
    launch_kind = str(record.get("launch_kind") or "").strip()
    install_state = str(record.get("install_state") or "").strip()

    if install_state not in {"installed", "source_available"}:
        return {
            "proof_capability": "NOT_INSTALLED",
            "proof_capability_label": "Install first",
            "proof_gap_reason": "The app is not installed, so no local proof command can run yet.",
            "proof_next_action": "Install or sync the source checkout before adding proof coverage.",
        }

    if section == "three_d_generation":
        return {
            "proof_capability": "MODEL_RUNTIME_PROOF_REQUIRED",
            "proof_capability_label": "Model runtime proof required",
            "proof_gap_reason": (
                "This Gen3D row needs real model/runtime evidence; LM Studio does not count "
                "as modeling readiness."
            ),
            "proof_next_action": (
                "Add a non-mutating verifier for the actual ONNX/safetensors/checkpoint/"
                "torch/ComfyUI runtime."
            ),
        }

    if section == "firmware" or launch_kind == "firmware_source":
        return {
            "proof_capability": "FIRMWARE_SOURCE_FROZEN",
            "proof_capability_label": "Firmware source frozen",
            "proof_gap_reason": (
                "Firmware rows are source references; runtime/update actions require operator "
                "review and hardware policy."
            ),
            "proof_next_action": "Use source checksum/version proof only; do not run firmware actions automatically.",
        }

    if _is_reference_only(section, launch_kind):
        return {
            "proof_capability": "REFERENCE_ONLY",
            "proof_capability_label": "Reference only",
            "proof_gap_reason": "This registry row is a read-only catalog/source reference, not a runnable app.",
            "proof_next_action": "Keep actions disabled unless a real adapter and verifier are added.",
        }

    if launch_kind in {"desktop_app", "desktop_or_cli"}:
        return {
            "proof_capability": "DESKTOP_PROOF_REQUIRED",
            "proof_capability_label": "Desktop proof required",
            "proof_gap_reason": "A desktop/CLI verifier has not been registered for this app.",
            "proof_next_action": "Add a read-only version/metadata command before enabling proof sweep.",
        }

    if launch_kind in {"service", "web_app", "gpu_worker"} or section in {
        "print_farm",
        "slicers",
        "modelers",
        "library",
        "materials",
    }:
        return {
            "proof_capability": "RUNTIME_PROOF_REQUIRED",
            "proof_capability_label": "Runtime proof required",
            "proof_gap_reason": "This app may be runnable, but no safe runtime verifier is configured.",
            "proof_next_action": "Register a bounded read-only health/version proof command.",
        }

    return {
        "proof_capability": "PROOF_COMMAND_MISSING",
        "proof_capability_label": "Proof command missing",
        "proof_gap_reason": "No safe proof contract has been classified for this row yet.",
        "proof_next_action": "Add a safe proof command or explicitly mark the row reference-only.",
    }


def _is_reference_only(section: str, launch_kind: str) -> bool:
    if section in {"hardware", "research"}:
        return True
    return launch_kind in {
        "catalog_reference",
        "hardware_reference",
        "reference",
        "rust_library_reference",
        "service_reference",
        "source_reference",
        "touch_ui_reference",
        "web_app_reference",
    }
