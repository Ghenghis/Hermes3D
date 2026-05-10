"""Firmware/farm source inventory probe tests (I7 — read-only, no flash/compile/serial).

Tests for :func:`probe_firmware_source_inventory` and :func:`probe_all_firmware_sources`
in ``hermes3d.services.module_runtime``.

ABSOLUTE CONSTRAINTS verified by these tests:
- No flash commands (avrdude, dfu-util, openocd, esptool, etc.)
- No serial port connections
- No build / compile (make, cmake, platformio)
- S1 (192.168.0.12) is not probed here
- T1 / V400: source repos only — printers not probed
- All firmware rows: runner_status=source_reference_only, agent_executable=False
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from hermes3d.services.module_runtime import (
    FIRMWARE_RUNNER_CONTRACT_TEMPLATE,
    FIRMWARE_SOURCE_PATHS,
    _git_describe,
    probe_all_firmware_sources,
    probe_firmware_source_inventory,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXPECTED_FIRMWARE_MODULE_IDS = {
    "firmware_klipper",
    "marlin",
    "prusa_firmware",
    "reprapfirmware",
    "repetier_firmware",
    "smoothieware",
}


# ---------------------------------------------------------------------------
# FIRMWARE_SOURCE_PATHS registry tests
# ---------------------------------------------------------------------------


class TestFirmwareSourcePathsRegistry:
    """All expected firmware module IDs must be registered."""

    def test_all_firmware_modules_registered(self) -> None:
        assert EXPECTED_FIRMWARE_MODULE_IDS == set(FIRMWARE_SOURCE_PATHS.keys())

    def test_all_paths_are_nonempty_strings(self) -> None:
        for mod_id, path in FIRMWARE_SOURCE_PATHS.items():
            assert isinstance(path, str), f"{mod_id}: path must be a string"
            assert path, f"{mod_id}: path must not be empty"

    def test_no_flash_tool_in_paths(self) -> None:
        """Source paths must not reference flash utilities."""
        forbidden = {"avrdude", "dfu-util", "openocd", "esptool", "platformio"}
        for mod_id, path in FIRMWARE_SOURCE_PATHS.items():
            for tool in forbidden:
                assert tool not in path.lower(), (
                    f"{mod_id}: path contains forbidden flash tool reference '{tool}'"
                )

    def test_no_s1_ip_in_paths(self) -> None:
        """S1 camera host must not appear in any firmware source path."""
        for mod_id, path in FIRMWARE_SOURCE_PATHS.items():
            assert "192.168.0.12" not in path, (
                f"{mod_id}: S1 camera IP must not appear in firmware source paths"
            )

    def test_klipper_firmware_path_is_source_lab(self) -> None:
        assert "source-lab" in FIRMWARE_SOURCE_PATHS["firmware_klipper"].replace("\\", "/")

    def test_marlin_path_is_source_lab(self) -> None:
        assert "source-lab" in FIRMWARE_SOURCE_PATHS["marlin"].replace("\\", "/")


# ---------------------------------------------------------------------------
# FIRMWARE_RUNNER_CONTRACT_TEMPLATE tests
# ---------------------------------------------------------------------------


class TestFirmwareRunnerContractTemplate:
    """Contract template must enforce source-reference-only policy."""

    def test_runner_status_is_source_reference_only(self) -> None:
        assert FIRMWARE_RUNNER_CONTRACT_TEMPLATE["runner_status"] == "source_reference_only"

    def test_runner_family_is_source_reference_only(self) -> None:
        assert FIRMWARE_RUNNER_CONTRACT_TEMPLATE["runner_family"] == "source_reference_only"

    def test_agent_executable_is_false(self) -> None:
        assert FIRMWARE_RUNNER_CONTRACT_TEMPLATE["agent_executable"] is False

    def test_mutation_allowed_is_false(self) -> None:
        assert FIRMWARE_RUNNER_CONTRACT_TEMPLATE["mutation_allowed"] is False

    def test_proof_gate_version_set(self) -> None:
        assert (
            FIRMWARE_RUNNER_CONTRACT_TEMPLATE["proof_gate_version"]
            == "firmware-source-inventory-v1"
        )


# ---------------------------------------------------------------------------
# _git_describe tests (mocked)
# ---------------------------------------------------------------------------


class TestGitDescribe:
    """_git_describe uses only git describe --tags --always (read-only)."""

    def test_returns_tag_when_repo_exists(self, tmp_path) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="v2.0.8-1-gabcdef0\n", stderr="")
            result = _git_describe(str(tmp_path))
        assert result == "v2.0.8-1-gabcdef0"
        # Verify only git describe was called, not make/cmake/avrdude etc.
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[:3] == ["git", "describe", "--tags"]
        assert "--always" in cmd

    def test_returns_none_when_path_not_dir(self, tmp_path) -> None:
        with patch("os.path.isdir", return_value=False):
            result = _git_describe(str(tmp_path / "nonexistent"))
        assert result is None

    def test_returns_none_on_timeout(self, tmp_path) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)),
        ):
            result = _git_describe(str(tmp_path))
        assert result is None

    def test_returns_none_on_oserror(self, tmp_path) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run", side_effect=OSError("git not found")),
        ):
            result = _git_describe(str(tmp_path))
        assert result is None

    def test_returns_none_when_stdout_empty(self, tmp_path) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not a git repo")
            result = _git_describe(str(tmp_path))
        assert result is None

    def test_strips_trailing_newline(self, tmp_path) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")
            result = _git_describe(str(tmp_path))
        assert result == "abc1234"

    def test_never_calls_flash_tools(self, tmp_path) -> None:
        """_git_describe must never invoke any flash utility."""
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="v1.0\n", stderr="")
            _git_describe(str(tmp_path))
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else call[1].get("args", [])
            cmd_str = " ".join(str(c) for c in cmd).lower()
            for forbidden in (
                "avrdude",
                "dfu-util",
                "openocd",
                "esptool",
                "make",
                "cmake",
                "platformio",
            ):
                assert forbidden not in cmd_str, (
                    f"_git_describe called forbidden tool '{forbidden}'"
                )


# ---------------------------------------------------------------------------
# probe_firmware_source_inventory tests (mocked)
# ---------------------------------------------------------------------------


class TestProbeFirmwareSourceInventory:
    """probe_firmware_source_inventory enforces read-only contract for each row."""

    @pytest.mark.parametrize("module_id", sorted(EXPECTED_FIRMWARE_MODULE_IDS))
    def test_structure_when_source_found(self, module_id: str) -> None:
        """When source dir exists and git describe succeeds, result must be well-formed."""
        with (
            patch("os.path.isdir", return_value=True),
            patch(
                "hermes3d.services.module_runtime._git_describe",
                return_value="v1.2.3-4-gabcdef0",
            ),
        ):
            result = probe_firmware_source_inventory(module_id)

        assert result["module_id"] == module_id
        assert result["source_found"] is True
        assert result["version_tag"] == "v1.2.3-4-gabcdef0"
        assert result["runner_status"] == "source_reference_only"
        assert result["runner_family"] == "source_reference_only"
        assert result["agent_executable"] is False
        assert result["mutation_allowed"] is False
        assert result["proof_gate_version"] == "firmware-source-inventory-v1"

    @pytest.mark.parametrize("module_id", sorted(EXPECTED_FIRMWARE_MODULE_IDS))
    def test_structure_when_source_absent(self, module_id: str) -> None:
        """When source dir is absent, result still has correct contract fields."""
        with patch("os.path.isdir", return_value=False):
            result = probe_firmware_source_inventory(module_id)

        assert result["module_id"] == module_id
        assert result["source_found"] is False
        assert result["version_tag"] is None
        assert result["runner_status"] == "source_reference_only"
        assert result["agent_executable"] is False
        assert result["mutation_allowed"] is False

    def test_unknown_module_id_returns_source_not_found(self) -> None:
        result = probe_firmware_source_inventory("totally_unknown_firmware")
        assert result["source_found"] is False
        assert result["source_path"] == ""
        assert result["version_tag"] is None
        assert result["runner_status"] == "source_reference_only"

    def test_source_path_matches_registry(self) -> None:
        with patch("os.path.isdir", return_value=False):
            for mod_id, expected_path in FIRMWARE_SOURCE_PATHS.items():
                result = probe_firmware_source_inventory(mod_id)
                assert result["source_path"] == expected_path, f"{mod_id}: source_path mismatch"

    def test_version_tag_is_none_when_git_fails(self) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("hermes3d.services.module_runtime._git_describe", return_value=None),
        ):
            result = probe_firmware_source_inventory("marlin")
        assert result["source_found"] is True
        assert result["version_tag"] is None


# ---------------------------------------------------------------------------
# probe_all_firmware_sources tests (mocked)
# ---------------------------------------------------------------------------


class TestProbeAllFirmwareSources:
    """probe_all_firmware_sources aggregates results for all firmware modules."""

    def test_returns_all_module_ids(self) -> None:
        with (
            patch("os.path.isdir", return_value=False),
        ):
            results = probe_all_firmware_sources()
        assert set(results.keys()) == EXPECTED_FIRMWARE_MODULE_IDS

    def test_each_result_has_required_keys(self) -> None:
        required_keys = {
            "module_id",
            "source_path",
            "source_found",
            "version_tag",
            "runner_status",
            "runner_family",
            "agent_executable",
            "mutation_allowed",
            "proof_gate_version",
        }
        with patch("os.path.isdir", return_value=False):
            results = probe_all_firmware_sources()
        for mod_id, result in results.items():
            missing = required_keys - set(result.keys())
            assert not missing, f"{mod_id}: result missing keys {missing}"

    def test_all_runner_statuses_are_source_reference_only(self) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("hermes3d.services.module_runtime._git_describe", return_value="v1.0"),
        ):
            results = probe_all_firmware_sources()
        for mod_id, result in results.items():
            assert result["runner_status"] == "source_reference_only", (
                f"{mod_id}: runner_status must be source_reference_only"
            )

    def test_all_are_not_agent_executable(self) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("hermes3d.services.module_runtime._git_describe", return_value="v1.0"),
        ):
            results = probe_all_firmware_sources()
        for mod_id, result in results.items():
            assert result["agent_executable"] is False, (
                f"{mod_id}: firmware must never be agent_executable"
            )

    def test_all_are_not_mutation_allowed(self) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("hermes3d.services.module_runtime._git_describe", return_value="v1.0"),
        ):
            results = probe_all_firmware_sources()
        for mod_id, result in results.items():
            assert result["mutation_allowed"] is False, (
                f"{mod_id}: firmware must never allow mutation"
            )

    def test_klipper_firmware_source_path_contains_klipper(self) -> None:
        with patch("os.path.isdir", return_value=False):
            results = probe_all_firmware_sources()
        assert (
            "Klipper" in results["firmware_klipper"]["source_path"]
            or "klipper" in results["firmware_klipper"]["source_path"].lower()
        )

    @pytest.mark.parametrize(
        "module_id,expected_fragment",
        [
            ("firmware_klipper", "Klipper"),
            ("marlin", "Marlin"),
            ("prusa_firmware", "Prusa"),
            ("reprapfirmware", "RepRap"),
            ("repetier_firmware", "Repetier"),
            ("smoothieware", "Smoothieware"),
        ],
    )
    def test_source_paths_match_firmware_name(self, module_id: str, expected_fragment: str) -> None:
        with patch("os.path.isdir", return_value=False):
            results = probe_all_firmware_sources()
        assert expected_fragment in results[module_id]["source_path"], (
            f"{module_id}: source_path should contain '{expected_fragment}'"
        )


# ---------------------------------------------------------------------------
# Safety constraint enforcement tests
# ---------------------------------------------------------------------------


class TestFirmwareSafetyConstraints:
    """Verify no forbidden operations can be triggered through the probe API."""

    def test_probe_does_not_call_make(self) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="v1.0\n", stderr="")
            probe_firmware_source_inventory("marlin")
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else []
            assert "make" not in cmd, "probe must not call 'make'"
            assert "cmake" not in cmd, "probe must not call 'cmake'"

    def test_probe_does_not_call_avrdude(self) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="v1.0\n", stderr="")
            probe_firmware_source_inventory("marlin")
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else []
            cmd_str = " ".join(str(c) for c in cmd).lower()
            assert "avrdude" not in cmd_str, "probe must not call avrdude"
            assert "dfu-util" not in cmd_str, "probe must not call dfu-util"
            assert "openocd" not in cmd_str, "probe must not call openocd"
            assert "esptool" not in cmd_str, "probe must not call esptool"

    def test_probe_does_not_call_platformio(self) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="v1.0\n", stderr="")
            probe_firmware_source_inventory("smoothieware")
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else []
            cmd_str = " ".join(str(c) for c in cmd).lower()
            assert "platformio" not in cmd_str, "probe must not call platformio"
            assert "pio" not in cmd_str.split(), "probe must not call pio"

    def test_probe_all_firmware_sources_does_not_call_flash_tools(self) -> None:
        with (
            patch("os.path.isdir", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="v1.0\n", stderr="")
            probe_all_firmware_sources()
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else []
            cmd_str = " ".join(str(c) for c in cmd).lower()
            for forbidden in (
                "avrdude",
                "dfu-util",
                "openocd",
                "esptool",
                "platformio",
                "make",
                "cmake",
            ):
                assert forbidden not in cmd_str, (
                    f"probe_all_firmware_sources called forbidden tool '{forbidden}'"
                )
