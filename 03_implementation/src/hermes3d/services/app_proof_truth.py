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


def _truth(
    *,
    capability: str,
    label: str,
    gap_reason: str | None,
    next_action: str,
    blocker_accepted: bool = False,
    acceptance_status: str | None = None,
    completion_state: str,
    runtime_requirements: list[str] | None = None,
    lm_studio_counts_for_modeling: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "proof_capability": capability,
        "proof_capability_label": label,
        "proof_gap_reason": gap_reason,
        "proof_next_action": next_action,
        "proof_blocker_accepted": blocker_accepted,
        "proof_acceptance_status": acceptance_status,
        "proof_completion_state": completion_state,
    }
    if runtime_requirements is not None:
        payload["proof_runtime_requirements"] = runtime_requirements
    if lm_studio_counts_for_modeling is not None:
        payload["lm_studio_counts_for_modeling"] = lm_studio_counts_for_modeling
    return payload


def classify_app_proof(record: dict[str, Any]) -> dict[str, Any]:
    """Return explicit proof truth metadata for a registry row."""
    proof_command = str(record.get("proof_command") or "").strip()
    if proof_command:
        return _truth(
            capability="COMMAND_PROOF",
            label="Command proof available",
            gap_reason=None,
            next_action="Run the seeded proof command to refresh pass/fail evidence.",
            completion_state="command_proof_available",
        )

    section = str(record.get("section") or "").strip()
    launch_kind = str(record.get("launch_kind") or "").strip()
    install_state = str(record.get("install_state") or "").strip()

    if install_state not in {"installed", "source_available"}:
        return _truth(
            capability="NOT_INSTALLED",
            label="Install first",
            gap_reason="The app is not installed, so no local proof command can run yet.",
            next_action="Install or sync the source checkout before adding proof coverage.",
            completion_state="not_installed",
        )

    if section == "three_d_generation":
        return _truth(
            capability="MODEL_RUNTIME_PROOF_REQUIRED",
            label="Model runtime proof required",
            gap_reason=(
                "This Gen3D row needs real model/runtime evidence; LM Studio does not count "
                "as modeling readiness."
            ),
            next_action=(
                "Add a non-mutating verifier for the actual ONNX/safetensors/checkpoint/"
                "torch/ComfyUI runtime."
            ),
            blocker_accepted=True,
            acceptance_status="accepted_blocked_model_runtime",
            completion_state="accepted_blocked",
            runtime_requirements=[
                "real model weights such as safetensors/checkpoints/ONNX files",
                "a reachable modeling runtime or a local artifact-producing pipeline",
                "artifact output evidence tied to Files/Artifacts lineage",
            ],
            lm_studio_counts_for_modeling=False,
        )

    if section == "firmware" or launch_kind == "firmware_source":
        return _truth(
            capability="FIRMWARE_SOURCE_FROZEN",
            label="Firmware source frozen",
            gap_reason=(
                "Firmware rows are source references; runtime/update actions require operator "
                "review and hardware policy."
            ),
            next_action="Use source checksum/version proof only; do not run firmware actions automatically.",
            blocker_accepted=True,
            acceptance_status="accepted_blocked_firmware_policy",
            completion_state="accepted_blocked",
        )

    if _is_reference_only(section, launch_kind):
        return _truth(
            capability="REFERENCE_ONLY",
            label="Reference only",
            gap_reason="This registry row is a read-only catalog/source reference, not a runnable app.",
            next_action="Keep actions disabled unless a real adapter and verifier are added.",
            blocker_accepted=True,
            acceptance_status="accepted_reference_only",
            completion_state="accepted_blocked",
        )

    if launch_kind in {"desktop_app", "desktop_or_cli"}:
        return _truth(
            capability="DESKTOP_PROOF_REQUIRED",
            label="Desktop proof required",
            gap_reason=(
                "Headless CI cannot prove this desktop app safely without a registered "
                "read-only version/metadata command."
            ),
            next_action="Add a read-only version/metadata command before enabling proof sweep.",
            blocker_accepted=True,
            acceptance_status="accepted_blocked_desktop_verifier_missing",
            completion_state="accepted_blocked",
        )

    if launch_kind in {"service", "web_app", "gpu_worker"} or section in {
        "print_farm",
        "slicers",
        "modelers",
        "library",
        "materials",
    }:
        return _truth(
            capability="RUNTIME_PROOF_REQUIRED",
            label="Runtime proof required",
            gap_reason=(
                "This app may be runnable, but no bounded read-only runtime verifier is "
                "configured yet."
            ),
            next_action="Register a bounded read-only health/version proof command.",
            blocker_accepted=True,
            acceptance_status="accepted_blocked_runtime_verifier_missing",
            completion_state="accepted_blocked",
        )

    return _truth(
        capability="PROOF_COMMAND_MISSING",
        label="Proof command missing",
        gap_reason="No safe proof contract has been classified for this row yet.",
        next_action="Add a safe proof command or explicitly mark the row reference-only.",
        completion_state="unclassified_gap",
    )


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
