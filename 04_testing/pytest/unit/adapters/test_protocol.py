"""Phase 1 Task 15 — ToolAdapter Protocol + SkeletonAdapter base + discovery."""

from __future__ import annotations

import pytest
from hermes3d.adapters.base import SkeletonAdapter
from hermes3d.adapters.protocol import NotImplementedYet, ToolAdapter
from hermes3d.adapters.registry import (
    AdapterRegistry,
    all_registered,
    register,
)
from hermes3d.adapters.types import (
    Action,
    AdapterState,
    Confirmation,
    DetectResult,
)


class _Demo(SkeletonAdapter):
    """Minimal subclass for protocol-conformance testing."""

    key = "demo"
    display_name = "Demo"
    category = "external_app"
    dangerous = False

    def detect(self) -> DetectResult:
        return self._detect_result(False, AdapterState.UNINSTALLED, "demo never installs")

    def version(self) -> str | None:
        return None

    def capabilities(self) -> frozenset[str]:
        return frozenset({"cli"})


def test_skeleton_implements_protocol():
    a = _Demo()
    assert isinstance(a, ToolAdapter)


def test_skeleton_identity_constants():
    a = _Demo()
    assert a.key == "demo"
    assert a.display_name == "Demo"
    assert a.category == "external_app"
    assert a.dangerous is False


def test_skeleton_detect_returns_state():
    r = _Demo().detect()
    assert r.state == AdapterState.UNINSTALLED
    assert r.found is False


def test_phase3_methods_raise_not_implemented_yet():
    a = _Demo()
    with pytest.raises(NotImplementedYet, match="Phase 3"):
        a.validate()
    with pytest.raises(NotImplementedYet, match="Phase 3"):
        a.healthcheck()
    with pytest.raises(NotImplementedYet, match="Phase 3"):
        a.status()
    with pytest.raises(NotImplementedYet, match="Phase 3"):
        a.open_docked()
    with pytest.raises(NotImplementedYet, match="Phase 3"):
        a.open_undocked()
    with pytest.raises(NotImplementedYet, match="Phase 3"):
        a.open_external()
    with pytest.raises(NotImplementedYet, match="Phase 3"):
        a.detach_ui()


def test_phase6_methods_raise_not_implemented_yet():
    a = _Demo()
    with pytest.raises(NotImplementedYet, match="Phase 6"):
        a.dry_run(Action(kind="noop", payload={}))
    with pytest.raises(NotImplementedYet, match="Phase 6"):
        a.execute(
            Action(kind="noop", payload={}),
            Confirmation(
                user="u",
                ts_utc="t",
                printer_id=None,
                reason_text="r",
                dry_run_token="tok",
                signed_token="sig",
                policy_version="v4.1",
            ),
        )


def test_skeleton_subclass_must_override_detection_methods():
    """If a subclass forgets to override detect/version/capabilities, the base
    class raises NotImplementedYet so the failure is loud."""

    class _Incomplete(SkeletonAdapter):
        key = "x"
        display_name = "X"
        category = "external_app"
        dangerous = False

    a = _Incomplete()
    with pytest.raises(NotImplementedYet, match="subclass must override"):
        a.detect()
    with pytest.raises(NotImplementedYet, match="subclass must override"):
        a.version()
    with pytest.raises(NotImplementedYet, match="subclass must override"):
        a.capabilities()


# Discovery registry
def test_register_adds_class_and_all_registered_returns_it():
    """The registry is module-global; tests register/clean up explicitly."""
    reg = AdapterRegistry()
    reg.register(_Demo)
    assert _Demo in reg.all()
    assert reg.by_key("demo") is _Demo
    # Constructing returns an instance
    inst = reg.instantiate("demo")
    assert isinstance(inst, _Demo)


def test_global_register_decorator_makes_adapter_discoverable():
    """The module-level `register` is a decorator that adds to a default registry."""

    # Use a fresh class so we don't pollute test order; cleanup at the end.
    @register
    class _Marker(SkeletonAdapter):
        key = "marker_test_only"
        display_name = "Marker"
        category = "external_app"
        dangerous = False

        def detect(self) -> DetectResult:
            return self._detect_result(False, AdapterState.UNINSTALLED)

        def version(self) -> str | None:
            return None

        def capabilities(self) -> frozenset[str]:
            return frozenset({"cli"})

    try:
        assert _Marker in all_registered()
    finally:
        # Keep the global registry clean across tests.
        from hermes3d.adapters.registry import _DEFAULT_REGISTRY  # noqa: PLC2701

        _DEFAULT_REGISTRY._classes.pop("marker_test_only", None)


def test_registry_rejects_duplicate_keys():
    reg = AdapterRegistry()
    reg.register(_Demo)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(_Demo)


def test_registry_rejects_class_with_empty_key():
    class _Bad(SkeletonAdapter):
        key = ""
        display_name = "Bad"
        category = "external_app"
        dangerous = False

    reg = AdapterRegistry()
    with pytest.raises(ValueError, match="non-empty 'key'"):
        reg.register(_Bad)
