"""Unit tests for real CAD provider health probes and template discovery.

All tests exercise real code paths — no mocking of shutil.which or importlib
that would hide integration failures.  Tests that depend on optional tools
(OpenSCAD, Blender, FreeCAD) are marked with the appropriate xfail/skip so
the suite stays green on a machine where those tools are absent.
"""

from __future__ import annotations

import importlib
import importlib.util
import shutil
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the module under test.  If the hermes3d package is not installed we
# skip the whole module rather than fail with ImportError at collection time.
# ---------------------------------------------------------------------------

try:
    from hermes3d.api.routes.design import (
        _discover_templates,
        _probe_cli_provider,
        _probe_providers,
        _probe_python_provider,
    )

    _MODULE_AVAILABLE = True
except ImportError:
    _MODULE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _MODULE_AVAILABLE,
    reason="hermes3d.api.routes.design not importable in this environment",
)


# ---------------------------------------------------------------------------
# _discover_templates
# ---------------------------------------------------------------------------


class TestDiscoverTemplates:
    def test_returns_list(self) -> None:
        result = _discover_templates()
        assert isinstance(result, list)

    def test_desk_organizer_present(self) -> None:
        result = _discover_templates()
        ids = [t["id"] for t in result]
        assert "desk_organizer" in ids, f"Expected 'desk_organizer' in {ids}"

    def test_each_entry_has_required_keys(self) -> None:
        result = _discover_templates()
        for entry in result:
            for key in (
                "id",
                "name",
                "executor_available",
                "executor_detail",
                "deps_ok",
                "missing_deps",
            ):
                assert key in entry, f"Template {entry.get('id')!r} missing key {key!r}"

    def test_executor_available_is_bool(self) -> None:
        result = _discover_templates()
        for entry in result:
            assert isinstance(entry["executor_available"], bool), (
                f"executor_available for {entry['id']!r} should be bool, got {type(entry['executor_available'])}"
            )

    def test_missing_deps_is_list(self) -> None:
        result = _discover_templates()
        for entry in result:
            assert isinstance(entry["missing_deps"], list), (
                f"missing_deps for {entry['id']!r} should be list, got {type(entry['missing_deps'])}"
            )

    def test_desk_organizer_executor_detail_nonempty(self) -> None:
        result = _discover_templates()
        desk = next((t for t in result if t["id"] == "desk_organizer"), None)
        assert desk is not None
        assert isinstance(desk["executor_detail"], str) and len(desk["executor_detail"]) > 0

    def test_preview_not_available_without_renderer(self) -> None:
        """preview_available must be False when no 3-D renderer is detected."""
        result = _discover_templates()
        for entry in result:
            # All current templates explicitly set preview_available=False
            assert entry.get("preview_available") is not True, (
                f"Template {entry['id']!r} claims preview_available=True but no renderer is wired."
            )


# ---------------------------------------------------------------------------
# _probe_providers
# ---------------------------------------------------------------------------


class TestProbeProviders:
    def test_returns_list(self) -> None:
        result = _probe_providers()
        assert isinstance(result, list)

    def test_expected_provider_ids_present(self) -> None:
        result = _probe_providers()
        ids = {p["id"] for p in result}
        for expected in ("openscad", "blender", "cadquery", "trimesh", "manifold3d", "freecad"):
            assert expected in ids, f"Expected provider id {expected!r} in {ids}"

    def test_each_provider_has_required_keys(self) -> None:
        required = (
            "id",
            "name",
            "kind",
            "status",
            "detected",
            "path",
            "capabilities",
            "detail",
            "probed_at",
        )
        result = _probe_providers()
        for provider in result:
            for key in required:
                assert key in provider, f"Provider {provider.get('id')!r} missing key {key!r}"

    def test_status_values_are_valid(self) -> None:
        valid = {"ready", "detected", "not_installed"}
        result = _probe_providers()
        for provider in result:
            assert provider["status"] in valid, (
                f"Provider {provider['id']!r} has invalid status {provider['status']!r}"
            )

    def test_detected_is_bool(self) -> None:
        result = _probe_providers()
        for provider in result:
            assert isinstance(provider["detected"], bool), (
                f"detected for {provider['id']!r} should be bool"
            )

    def test_capabilities_is_list(self) -> None:
        result = _probe_providers()
        for provider in result:
            assert isinstance(provider["capabilities"], list), (
                f"capabilities for {provider['id']!r} should be list"
            )

    def test_trimesh_status_matches_importability(self) -> None:
        """trimesh probe must reflect reality — not a hardcoded value."""
        result = _probe_providers()
        trimesh_entry = next((p for p in result if p["id"] == "trimesh"), None)
        assert trimesh_entry is not None
        spec = importlib.util.find_spec("trimesh")
        if spec is not None:
            assert trimesh_entry["detected"] is True
            assert trimesh_entry["status"] in {"ready", "detected"}
        else:
            assert trimesh_entry["detected"] is False
            assert trimesh_entry["status"] == "not_installed"

    def test_manifold3d_status_matches_importability(self) -> None:
        """manifold3d probe must reflect reality."""
        result = _probe_providers()
        m3d = next((p for p in result if p["id"] == "manifold3d"), None)
        assert m3d is not None
        spec = importlib.util.find_spec("manifold3d")
        if spec is not None:
            assert m3d["detected"] is True
        else:
            assert m3d["detected"] is False
            assert m3d["status"] == "not_installed"

    @pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD not installed")
    def test_openscad_ready_when_installed(self) -> None:
        result = _probe_providers()
        openscad = next((p for p in result if p["id"] == "openscad"), None)
        assert openscad is not None
        assert openscad["detected"] is True
        assert openscad["status"] in {"ready", "detected"}
        assert openscad["path"] is not None

    def test_openscad_not_installed_has_no_path(self) -> None:
        """If OpenSCAD is absent, path must be None — not a fabricated string."""
        openscad_fallback_paths = (
            r"C:\Program Files\OpenSCAD\openscad.exe",
            r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
        )
        if shutil.which("openscad") is not None or any(
            Path(p).exists() for p in openscad_fallback_paths
        ):
            pytest.skip("OpenSCAD is installed — skip the not_installed assertion")
        result = _probe_providers()
        openscad = next((p for p in result if p["id"] == "openscad"), None)
        assert openscad is not None
        assert openscad["path"] is None
        assert openscad["status"] == "not_installed"
        assert openscad["detected"] is False


# ---------------------------------------------------------------------------
# _probe_cli_provider (unit-level, parametric)
# ---------------------------------------------------------------------------


class TestProbeCliProvider:
    def test_nonexistent_exe_returns_not_installed(self) -> None:
        result = _probe_cli_provider(
            provider_id="test_nonexistent",
            display_name="NonExistent Tool",
            kind="test",
            exe_names=["__nonexistent_hermes3d_test_binary__"],
            version_args=["--version"],
            capabilities=["cap_a"],
            docs_url="https://example.com",
        )
        assert result["status"] == "not_installed"
        assert result["detected"] is False
        assert result["path"] is None

    def test_result_has_probed_at(self) -> None:
        result = _probe_cli_provider(
            provider_id="test2",
            display_name="Test",
            kind="test",
            exe_names=["__nonexistent__"],
            version_args=[],
            capabilities=[],
            docs_url="",
        )
        assert "probed_at" in result and isinstance(result["probed_at"], str)


# ---------------------------------------------------------------------------
# _probe_python_provider (unit-level)
# ---------------------------------------------------------------------------


class TestProbePythonProvider:
    def test_missing_module_returns_not_installed(self) -> None:
        result = _probe_python_provider(
            provider_id="test_missing",
            display_name="Missing Module",
            kind="python_lib",
            module_name="__hermes3d_nonexistent_module__",
            capabilities=["cap_x"],
            docs_url="https://example.com",
        )
        assert result["status"] == "not_installed"
        assert result["detected"] is False
        assert result["path"] is None
        assert result["version"] is None

    def test_existing_stdlib_module_returns_ready(self) -> None:
        """Use a guaranteed-present stdlib module (json) as a smoke test."""
        result = _probe_python_provider(
            provider_id="json_smoke",
            display_name="json (stdlib)",
            kind="python_stdlib",
            module_name="json",
            capabilities=["serialisation"],
            docs_url="https://docs.python.org/3/library/json.html",
        )
        assert result["detected"] is True
        assert result["status"] in {"ready", "detected"}

    def test_result_has_probed_at(self) -> None:
        result = _probe_python_provider(
            provider_id="ts",
            display_name="Test",
            kind="test",
            module_name="__hermes3d_nonexistent_module__",
            capabilities=[],
            docs_url="",
        )
        assert "probed_at" in result and isinstance(result["probed_at"], str)
