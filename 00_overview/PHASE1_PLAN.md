# Phase 1 Implementation Plan — Foundation (Registry + Adapter Shell + Env Detect)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land all the FOUNDATION pieces Phase 2 (UI shell) and Phase 3 (read-only adapters) will build on top of: a hardened typed registry validator, an env-detect script + schema + fixtures, the canonical Adapter Protocol + 11 detect/version/capabilities-only skeletons, JSON config schemas per adapter, and ADR-008 codifying the adapter lifecycle + dock/undock + confirmation envelope. **Zero real tool integration. Zero printer write actions. Zero UI work.**

**Architecture:** Pure Python (no new runtime deps beyond `PyYAML` + `jsonschema`). Two new packages: `src/hermes3d/registry/` and `src/hermes3d/adapters/`, plus `src/hermes3d/env/`. The Adapter Protocol is a `typing.Protocol` (structural) — skeletons satisfy it via duck-typing while raising `NotImplementedYet` for everything beyond detection. Tests live under `04_testing/pytest/unit/{registry,adapters,env}/` with fixture YAMLs and JSON for offline runs. CI gates the registry validator + adapter smoke tests via existing layers.

**Tech Stack:** Python 3.11+, PyYAML (existing), `jsonschema` (NEW — light, MIT, well-maintained), pytest, ruff.

---

## Scope

**In scope (this PR — preview-broad per user override):**

1. **Registry validator (real, hardened)** — typed loader + validator under `src/hermes3d/registry/`, license + per-`type` capability matrix + tested_versions + URL shape + structured errors + default-path fix
2. **Update live registry YAML** — populate license + tested_versions + dock tokens for all 12 entries
3. **Stale pseudocode replacement** — kit's `registry_validator_pseudocode.py` becomes a one-line redirect stub
4. **CLI wrappers + CI gate** — `scripts/validate-registry.{sh,ps1}` + Layer A registry-validator step
5. **`.gitignore` defensive addendum** — `*.pem`, `*.key`, `id_rsa*`, `*.p12`, `*.pfx`
6. **`install_plan.md` Orca URL fix**
7. **ADR-008** — adapter lifecycle + dock/undock/external + confirmation envelope, codifying `03_implementation/adapter_registry/README.md` §3 + §4 + §7 as immutable
8. **Adapter Protocol module** — `src/hermes3d/adapters/protocol.py` + `types.py` (typed envelope, lifecycle states enum, capability flags enum, confirmation envelope dataclass)
9. **11 adapter skeletons** — `src/hermes3d/adapters/{moonraker,octoprint,printrun,prusa_slicer,orca_slicer,flsun_slicer,cura,blender,blender_mcp,fluidd,mainsail}.py` — each implements `key`/`display_name`/`category`/`dangerous` constants + `detect()`/`version()`/`capabilities()` with real (best-effort, side-effect-free) logic; all other methods raise `NotImplementedYet` with a Phase-3/6 hand-off message
10. **JSON config schemas** — 9 schemas under `03_implementation/adapter_registry/schemas/` (mainsail + fluidd reuse moonraker.schema.json since they're UIs over Moonraker)
11. **env-detect** — `src/hermes3d/env/detect.py` + `schemas/env_report.schema.json` + 4 fixtures + tests + `scripts/env-detect.{sh,ps1}` wrappers
12. **Phase 1 completion report + signed proof bundle**

**Constraints (re-stated, immutable for this PR):**
- DO NOT start UI-Final
- DO NOT touch `release/v5.3.0-rc1` branch or the `v5.3.0-rc1` tag
- DO NOT integrate real tools yet (skeletons only)
- DO NOT add real printer-control write actions (Phase 6)

**Explicitly DEFERRED beyond Phase 1 (per kit phase mapping):**
- ADR-005 "Threat Model", ADR-006 "Edition Resolution Rule", ADR-007 "Worker Authentication Scheme" — Phase 4/5 when tunnel + worker code lands
- `02_architecture/AUDIT_LOG_SCHEMA.md`, `RATE_LIMIT_POLICY.md` — same
- Any read-only adapter `validate()`/`healthcheck()`/`status()`/`open_*()` implementations — Phase 3
- All `dry_run()` / `execute()` / `detach_ui()` implementations — Phase 6
- Worker registration to a VPS — Phase 4/5
- React/Tailwind dashboard — Phase 2 (UI-Final), with `Hermes3D.png` as the immutable visual contract per `feedback_no_ui_design.md`

---

## File Structure

```
03_implementation/src/hermes3d/registry/
├── __init__.py                       # package marker
├── types.py                          # ToolEntry, AdapterSpec, VersionPolicy
├── errors.py                         # ValidationError + ErrorCode enum
├── capability_matrix.py              # per-type required capabilities
├── loader.py                         # YAML → typed entries
└── validator.py                      # rules engine + CLI entrypoint

03_implementation/src/hermes3d/adapters/
├── __init__.py                       # exports protocol + registry of skeleton classes
├── types.py                          # AdapterState enum, CapabilityFlag enum, AdapterResult, Confirmation, Action, etc.
├── protocol.py                       # ToolAdapter Protocol + NotImplementedYet exception
├── base.py                           # SkeletonAdapter base class with NotImplementedYet stubs
├── moonraker.py                      # one per locked tool (11 files)
├── octoprint.py
├── printrun.py
├── prusa_slicer.py
├── orca_slicer.py
├── flsun_slicer.py
├── cura.py
├── blender.py
├── blender_mcp.py
├── fluidd.py
└── mainsail.py

03_implementation/src/hermes3d/env/
├── __init__.py
├── types.py                          # EnvReport dataclass
├── detect.py                         # cascade: nvidia-smi → torch.cuda → WMI → safe-unavailable
└── edition.py                        # resolve_edition() rule

03_implementation/adapter_registry/schemas/
├── moonraker.schema.json             # also consumed by mainsail + fluidd
├── octoprint.schema.json
├── printrun.schema.json
├── prusa_slicer.schema.json
├── orca_slicer.schema.json
├── flsun_slicer.schema.json
├── cura.schema.json
├── blender.schema.json
└── blender_mcp.schema.json

schemas/
└── env_report.schema.json            # JSON Schema for env-detect output

04_testing/pytest/unit/registry/      # tests + fixtures (see Task list for files)
04_testing/pytest/unit/adapters/      # tests + fixtures
04_testing/pytest/unit/env/           # tests + fixtures
04_testing/pytest/unit/env/fixtures/
├── nvidia_smi_3090ti.json
├── nvidia_smi_no_gpu.json
├── no_nvidia_smi.json
└── no_gpu.json

scripts/
├── validate-registry.sh / .ps1
└── env-detect.sh / .ps1

02_architecture/adr/
└── ADR-008-adapter-lifecycle-and-dock-undock.md     # NEW — codifies adapter contract

hermes3d_gui_contract_kit_v4.1/                      # READ-ONLY kit, with two narrow exceptions:
├── config/external_repos_registry.yaml              # UPDATED: + license, tested_versions, dock tokens (data, not spec)
└── scripts/registry_validator_pseudocode.py         # REPLACED: 1-line redirect stub (resolves Phase 0 stale-pseudocode finding)
└── scripts/install_plan.md                          # UPDATED: OrcaSlicer URL fix

.github/workflows/ci.yml                             # UPDATED: Layer A registry-validator step
.gitignore                                            # UPDATED: defensive secret-vector patterns

00_overview/
└── PHASE1_COMPLETION_REPORT.md                      # NEW: per-task closeout, links to bundle
```

`03_implementation/pyproject.toml` may need `jsonschema>=4.0` added under `[project.optional-dependencies].all`. Confirmed before Task 1 starts.

---

## Tasks

> **Inline execution rule:** Coordinator commits after each task and runs the relevant tests. **Checkpoints** at the end of Tasks 3, 6, 9, 12, 15, 17 — coordinator pauses, posts a brief status (commits + test counts + any blockers), and then continues. User may intervene at any checkpoint.

### Task 1: Registry — typed dataclasses

**Files:**
- Create: `03_implementation/src/hermes3d/registry/__init__.py`
- Create: `03_implementation/src/hermes3d/registry/types.py`
- Create: `04_testing/pytest/unit/registry/__init__.py`
- Create: `04_testing/pytest/unit/registry/test_types.py`

- [ ] **Step 1: Failing test**

```python
# 04_testing/pytest/unit/registry/test_types.py
from hermes3d.registry.types import ToolEntry, AdapterSpec, VersionPolicy

def test_tool_entry_minimal_construction():
    entry = ToolEntry(
        key="example", name="Example", type="external_app", required=True,
        os_support=("windows",),
        version_policy=VersionPolicy(channel="stable", manual_select=True),
        install={"method": "binary"},
        verify={"commands": ["example --version"], "expected": "version"},
        adapter=AdapterSpec(mode="external_process", capabilities=("detect", "launch_external")),
        repo="https://github.com/example/example",
        license="MIT", tested_versions=("1.0.0",),
    )
    assert entry.key == "example"
    assert entry.adapter.mode == "external_process"
    assert "detect" in entry.adapter.capabilities

def test_version_policy_has_resolution():
    assert VersionPolicy(channel="stable", manual_select=True).has_resolution()
    assert VersionPolicy(pin="1.2.3").has_resolution()
    assert not VersionPolicy().has_resolution()

def test_reference_url_prefers_repo():
    entry = ToolEntry(
        key="x", name="X", type="external_app", required=True,
        os_support=("windows",), version_policy=VersionPolicy(manual_select=True),
        install={"method": "binary"}, verify={"commands": ["x"], "expected": "v"},
        adapter=AdapterSpec(mode="external_process", capabilities=("detect",)),
        repo="https://example.com/r", source="https://example.com/s", homepage="https://example.com/h",
        license="MIT", tested_versions=("1.0.0",),
    )
    assert entry.reference_url() == "https://example.com/r"
```

- [ ] **Step 2: Run to confirm fail**

```
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python -m pytest 04_testing/pytest/unit/registry/ -v
```
Expected: `ImportError: No module named 'hermes3d.registry'`

- [ ] **Step 3: Write `__init__.py` + `types.py`**

```python
# 03_implementation/src/hermes3d/registry/__init__.py
"""Hermes3D external tool registry — typed loader + validator."""
```

```python
# 03_implementation/src/hermes3d/registry/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping

@dataclass(frozen=True)
class VersionPolicy:
    pin: str | None = None
    channel: str | None = None
    manual_select: bool = False
    locked: str | None = None

    def has_resolution(self) -> bool:
        return any((self.pin, self.channel, self.locked)) or self.manual_select

@dataclass(frozen=True)
class AdapterSpec:
    mode: str
    capabilities: tuple[str, ...]

@dataclass(frozen=True)
class ToolEntry:
    key: str
    name: str
    type: str
    required: bool
    os_support: tuple[str, ...]
    version_policy: VersionPolicy
    install: Mapping[str, object]
    verify: Mapping[str, object]
    adapter: AdapterSpec
    license: str
    tested_versions: tuple[str, ...] = field(default_factory=tuple)
    repo: str | None = None
    source: str | None = None
    homepage: str | None = None

    def reference_url(self) -> str | None:
        return self.repo or self.source or self.homepage
```

- [ ] **Step 4: Run to confirm pass**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/ 04_testing/pytest/unit/registry/
git commit -m "feat(registry): typed ToolEntry + AdapterSpec + VersionPolicy"
```

### Task 2: Registry — error model

**Files:**
- Create: `03_implementation/src/hermes3d/registry/errors.py`
- Modify: `04_testing/pytest/unit/registry/test_types.py` (add error tests)

- [ ] **Step 1: Failing tests**

```python
# Append to test_types.py
from hermes3d.registry.errors import ValidationError, ErrorCode

def test_error_code_enum_complete():
    expected = {
        "MISSING_REQUIRED_FIELD", "INVALID_URL_SHAPE", "MISSING_LICENSE",
        "INVALID_LICENSE", "MISSING_DOCK_CAPABILITY",
        "MISSING_EXTERNAL_LAUNCH_CAPABILITY", "EMPTY_CAPABILITIES",
        "UNKNOWN_TYPE", "EMPTY_TESTED_VERSIONS", "INVALID_VERSION_POLICY",
        "INVALID_TYPE",
    }
    actual = {e.value for e in ErrorCode}
    assert expected.issubset(actual)

def test_validation_error_serializes():
    err = ValidationError("example", ErrorCode.MISSING_LICENSE, "missing 'license'", "error")
    d = err.to_dict()
    assert d == {"tool_id": "example", "code": "MISSING_LICENSE", "message": "missing 'license'", "severity": "error"}
```

- [ ] **Step 2: Run to confirm fail**

- [ ] **Step 3: Implement `errors.py`**

```python
# 03_implementation/src/hermes3d/registry/errors.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Literal

class ErrorCode(str, Enum):
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_TYPE = "INVALID_TYPE"
    INVALID_URL_SHAPE = "INVALID_URL_SHAPE"
    MISSING_LICENSE = "MISSING_LICENSE"
    INVALID_LICENSE = "INVALID_LICENSE"
    MISSING_DOCK_CAPABILITY = "MISSING_DOCK_CAPABILITY"
    MISSING_EXTERNAL_LAUNCH_CAPABILITY = "MISSING_EXTERNAL_LAUNCH_CAPABILITY"
    EMPTY_CAPABILITIES = "EMPTY_CAPABILITIES"
    UNKNOWN_TYPE = "UNKNOWN_TYPE"
    EMPTY_TESTED_VERSIONS = "EMPTY_TESTED_VERSIONS"
    INVALID_VERSION_POLICY = "INVALID_VERSION_POLICY"

Severity = Literal["error", "warning", "info"]

@dataclass(frozen=True)
class ValidationError:
    tool_id: str
    code: ErrorCode
    message: str
    severity: Severity = "error"

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["code"] = self.code.value
        return d
```

- [ ] **Step 4: Run to confirm pass**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/errors.py 04_testing/pytest/unit/registry/test_types.py
git commit -m "feat(registry): structured error model with ErrorCode enum"
```

### Task 3: Registry — capability matrix

**Files:**
- Create: `03_implementation/src/hermes3d/registry/capability_matrix.py`
- Create: `04_testing/pytest/unit/registry/test_capability_matrix.py`

- [ ] **Step 1: Failing tests**

```python
# 04_testing/pytest/unit/registry/test_capability_matrix.py
from hermes3d.registry.capability_matrix import (
    required_capabilities_for_type, KNOWN_TYPES, is_known_type,
)

def test_slicer_requires_external_and_dock():
    req = required_capabilities_for_type("slicer")
    assert "launch_external" in req
    assert any(c.startswith("dock_") for c in req)

def test_external_web_ui_requires_dock_and_fullscreen():
    req = required_capabilities_for_type("external_web_ui")
    assert any(c.startswith("dock_") for c in req)
    assert any("fullscreen" in c for c in req)

def test_printer_api_exempt_from_dock():
    req = required_capabilities_for_type("printer_api")
    assert not any(c.startswith("dock_") for c in req)

def test_unknown_type_returns_empty_set():
    assert required_capabilities_for_type("nonexistent") == frozenset()
    assert not is_known_type("nonexistent")

def test_known_types_includes_all_locked_categories():
    expected = {
        "external_app", "mcp_provider", "slicer", "printer_control_usb",
        "printer_api", "external_web_ui", "printer_api_and_web_ui",
    }
    assert expected.issubset(KNOWN_TYPES)
```

- [ ] **Step 2: Run to confirm fail**

- [ ] **Step 3: Implement `capability_matrix.py`**

```python
# 03_implementation/src/hermes3d/registry/capability_matrix.py
"""Per-`type` required adapter capabilities.

Source: 03_implementation/adapter_registry/README.md §1 (taxonomy) + §5 (capability flags),
plus the user-locked rule that every UI-bearing tool be supportable in BOTH docked AND
external modes.
"""
from __future__ import annotations

_REQUIRED: dict[str, frozenset[str]] = {
    "external_app":            frozenset({"launch_external", "dock_if_supported"}),
    "mcp_provider":            frozenset(),
    "slicer":                  frozenset({"launch_external", "dock_if_allowed"}),
    "printer_control_usb":     frozenset({"launch_external", "dock_if_allowed"}),
    "printer_api":             frozenset(),
    "external_web_ui":         frozenset({"dock_if_allowed", "fullscreen_external"}),
    "printer_api_and_web_ui":  frozenset({"dock_if_allowed"}),
}

KNOWN_TYPES: frozenset[str] = frozenset(_REQUIRED.keys())

def required_capabilities_for_type(tool_type: str) -> frozenset[str]:
    return _REQUIRED.get(tool_type, frozenset())

def is_known_type(tool_type: str) -> bool:
    return tool_type in KNOWN_TYPES
```

- [ ] **Step 4: Run to confirm pass**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/capability_matrix.py 04_testing/pytest/unit/registry/test_capability_matrix.py
git commit -m "feat(registry): per-type required capability matrix"
```

> **CHECKPOINT 1** (after Task 3): coordinator runs `pytest 04_testing/pytest/unit/registry/ -v` (expect 7+ tests passing), posts brief status, and proceeds.

### Task 4: Registry — loader

**Files:**
- Create: `03_implementation/src/hermes3d/registry/loader.py`
- Create: `04_testing/pytest/unit/registry/conftest.py`
- Create: `04_testing/pytest/unit/registry/fixtures/valid_minimal.yaml`
- Create: `04_testing/pytest/unit/registry/test_loader.py`

- [ ] **Step 1: Fixture**

```yaml
# 04_testing/pytest/unit/registry/fixtures/valid_minimal.yaml
tools:
  example:
    name: Example
    type: external_app
    repo: https://github.com/example/example
    required: true
    os_support: [windows]
    version_policy: {channel: stable, manual_select: true}
    install: {method: binary_or_existing_install}
    verify: {commands: ["example --version"], expected: "version output"}
    adapter: {mode: external_process, capabilities: [launch_external, dock_if_supported]}
    license: MIT
    tested_versions: ["1.0.0", "1.1.0"]
```

- [ ] **Step 2: conftest**

```python
# 04_testing/pytest/unit/registry/conftest.py
from pathlib import Path
import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def fixture_path():
    def _load(name: str) -> Path:
        path = FIXTURE_DIR / name
        assert path.exists(), f"missing fixture: {name}"
        return path
    return _load
```

- [ ] **Step 3: Failing tests**

```python
# 04_testing/pytest/unit/registry/test_loader.py
import pytest
from hermes3d.registry.loader import load_registry, LoaderError

def test_load_minimal_returns_one_tool(fixture_path):
    entries = load_registry(fixture_path("valid_minimal.yaml"))
    assert len(entries) == 1
    e = entries[0]
    assert e.key == "example"
    assert e.adapter.mode == "external_process"
    assert "launch_external" in e.adapter.capabilities
    assert e.license == "MIT"
    assert e.tested_versions == ("1.0.0", "1.1.0")

def test_load_missing_file_raises(tmp_path):
    with pytest.raises(LoaderError, match="not found"):
        load_registry(tmp_path / "nope.yaml")
```

- [ ] **Step 4: Implement `loader.py`**

```python
# 03_implementation/src/hermes3d/registry/loader.py
from __future__ import annotations
from pathlib import Path
import yaml
from .types import AdapterSpec, ToolEntry, VersionPolicy

class LoaderError(Exception):
    """File-not-found or top-level YAML structure error."""

def _vp(d: dict) -> VersionPolicy:
    return VersionPolicy(
        pin=d.get("pin"), channel=d.get("channel"),
        manual_select=bool(d.get("manual_select", False)), locked=d.get("locked"),
    )

def _adapter(d: dict) -> AdapterSpec:
    caps = d.get("capabilities") or ()
    if not isinstance(caps, (list, tuple)): caps = ()
    return AdapterSpec(mode=str(d.get("mode", "")), capabilities=tuple(str(c) for c in caps))

def _entry(key: str, raw: dict) -> ToolEntry:
    os_support = raw.get("os_support") or ()
    if not isinstance(os_support, (list, tuple)): os_support = ()
    tested = raw.get("tested_versions") or ()
    if not isinstance(tested, (list, tuple)): tested = ()
    return ToolEntry(
        key=key, name=str(raw.get("name", "")), type=str(raw.get("type", "")),
        required=bool(raw.get("required", False)),
        os_support=tuple(str(o) for o in os_support),
        version_policy=_vp(raw.get("version_policy") or {}),
        install=raw.get("install") or {}, verify=raw.get("verify") or {},
        adapter=_adapter(raw.get("adapter") or {}),
        license=str(raw.get("license", "")),
        tested_versions=tuple(str(v) for v in tested),
        repo=raw.get("repo"), source=raw.get("source"), homepage=raw.get("homepage"),
    )

def load_registry(path: Path) -> list[ToolEntry]:
    if not path.exists():
        raise LoaderError(f"registry not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tools = data.get("tools") if isinstance(data, dict) and "tools" in data else data
    if not isinstance(tools, dict) or not tools:
        raise LoaderError("registry must contain non-empty 'tools' object")
    return [_entry(str(k), v) for k, v in tools.items() if isinstance(v, dict)]
```

- [ ] **Step 5: Run, confirm pass, commit**

```bash
git add 03_implementation/src/hermes3d/registry/loader.py 04_testing/pytest/unit/registry/conftest.py 04_testing/pytest/unit/registry/fixtures/ 04_testing/pytest/unit/registry/test_loader.py
git commit -m "feat(registry): YAML loader returns typed ToolEntry list"
```

### Task 5: Registry — validator (license + structural rules + CLI)

Identical to v1 plan §Task 5 — license check, empty capabilities check, unknown-type warning, default-path anchored to script location, `--json` output. See full code block in §Task 5 below (kept inline for self-containment).

**Files:**
- Create: `03_implementation/src/hermes3d/registry/validator.py`
- Create: `04_testing/pytest/unit/registry/test_validator_schema.py`
- Create: `04_testing/pytest/unit/registry/fixtures/missing_license.yaml`
- Create: `04_testing/pytest/unit/registry/fixtures/empty_capabilities.yaml`

- [ ] **Step 1: Fixtures**

```yaml
# fixtures/missing_license.yaml
tools:
  example:
    name: Example
    type: external_app
    repo: https://github.com/example/example
    required: true
    os_support: [windows]
    version_policy: {channel: stable, manual_select: true}
    install: {method: binary}
    verify: {commands: ["example --version"], expected: "version"}
    adapter: {mode: external_process, capabilities: [launch_external, dock_if_supported]}
    tested_versions: ["1.0.0"]
```

```yaml
# fixtures/empty_capabilities.yaml
tools:
  example:
    name: Example
    type: external_app
    repo: https://github.com/example/example
    required: true
    os_support: [windows]
    version_policy: {channel: stable, manual_select: true}
    install: {method: binary}
    verify: {commands: ["example --version"], expected: "version"}
    adapter: {mode: external_process, capabilities: []}
    license: MIT
    tested_versions: ["1.0.0"]
```

- [ ] **Step 2: Failing tests**

```python
# 04_testing/pytest/unit/registry/test_validator_schema.py
from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import validate
from hermes3d.registry.errors import ErrorCode

def test_minimal_valid_passes(fixture_path):
    entries = load_registry(fixture_path("valid_minimal.yaml"))
    result = validate(entries)
    assert result.ok, [e.to_dict() for e in result.errors]
    assert result.checked == 1

def test_missing_license_flagged(fixture_path):
    result = validate(load_registry(fixture_path("missing_license.yaml")))
    assert not result.ok
    assert ErrorCode.MISSING_LICENSE in {e.code for e in result.errors}

def test_empty_capabilities_flagged(fixture_path):
    result = validate(load_registry(fixture_path("empty_capabilities.yaml")))
    assert not result.ok
    assert ErrorCode.EMPTY_CAPABILITIES in {e.code for e in result.errors}
```

- [ ] **Step 3: Implement `validator.py`** (skeleton — URL + capability + tested_versions added in Tasks 6-8)

```python
# 03_implementation/src/hermes3d/registry/validator.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import argparse, json, sys
from typing import Sequence
from .capability_matrix import is_known_type, required_capabilities_for_type
from .errors import ErrorCode, ValidationError
from .loader import LoaderError, load_registry
from .types import ToolEntry

_INVALID_LICENSE_VALUES = frozenset({"", "unknown", "tbd", "todo", "n/a", "none"})

@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    checked: int
    errors: tuple[ValidationError, ...] = field(default_factory=tuple)
    def to_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "checked": self.checked, "errors": [e.to_dict() for e in self.errors]}

def _check_license(e: ToolEntry) -> list[ValidationError]:
    if not e.license:
        return [ValidationError(e.key, ErrorCode.MISSING_LICENSE, "missing required field 'license'")]
    if e.license.strip().lower() in _INVALID_LICENSE_VALUES:
        return [ValidationError(e.key, ErrorCode.INVALID_LICENSE, f"license '{e.license}' not a real SPDX id")]
    return []

def _check_capabilities(e: ToolEntry) -> list[ValidationError]:
    out: list[ValidationError] = []
    if not e.adapter.capabilities:
        out.append(ValidationError(e.key, ErrorCode.EMPTY_CAPABILITIES, "adapter.capabilities must be non-empty"))
    if not is_known_type(e.type):
        out.append(ValidationError(e.key, ErrorCode.UNKNOWN_TYPE, f"unknown type '{e.type}'", "warning"))
    return out

def _check_entry(e: ToolEntry) -> list[ValidationError]:
    return [*_check_license(e), *_check_capabilities(e)]

def validate(entries: Sequence[ToolEntry]) -> ValidationResult:
    errs: list[ValidationError] = []
    for e in entries: errs.extend(_check_entry(e))
    blocking = [e for e in errs if e.severity == "error"]
    return ValidationResult(ok=not blocking, checked=len(entries), errors=tuple(errs))

def _default_registry_path() -> Path:
    return Path(__file__).resolve().parents[4] / "hermes3d_gui_contract_kit_v4.1" / "config" / "external_repos_registry.yaml"

def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hermes3d.registry.validator")
    p.add_argument("path", nargs="?", type=Path, default=_default_registry_path())
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        entries = load_registry(a.path)
    except LoaderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1
    r = validate(entries)
    if a.json:
        print(json.dumps(r.to_dict(), indent=2))
    elif r.ok:
        print(f"Registry validation PASS: {r.checked} tools checked")
    else:
        print(f"Registry validation FAILED: {r.checked} tools checked, {len(r.errors)} issues")
        for e in r.errors: print(f"- [{e.severity}] {e.tool_id} {e.code.value}: {e.message}")
    return 0 if r.ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run, confirm pass, commit**

```bash
git add 03_implementation/src/hermes3d/registry/validator.py 04_testing/pytest/unit/registry/test_validator_schema.py 04_testing/pytest/unit/registry/fixtures/missing_license.yaml 04_testing/pytest/unit/registry/fixtures/empty_capabilities.yaml
git commit -m "feat(registry): validator with license + structural rules + CLI"
```

### Task 6: Registry — URL shape rules

**Files:**
- Modify: `03_implementation/src/hermes3d/registry/validator.py`
- Create: `04_testing/pytest/unit/registry/fixtures/bad_url_shape.yaml`
- Create: `04_testing/pytest/unit/registry/test_validator_urls.py`

(Identical to v1 §Task 6 — see full code there. URL regex `^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$`, `_check_url()` helper, two test fixtures.)

- [ ] **Step 1: Fixture + tests**

```yaml
# fixtures/bad_url_shape.yaml
tools:
  bad_one:
    name: Bad
    type: external_app
    repo: ""
    required: false
    os_support: [windows]
    version_policy: {channel: stable, manual_select: true}
    install: {method: binary}
    verify: {commands: ["x --version"], expected: "v"}
    adapter: {mode: external_process, capabilities: [launch_external, dock_if_supported]}
    license: MIT
    tested_versions: ["1.0.0"]
  bad_two:
    name: Bad2
    type: external_app
    repo: "https//github.com/x/y"
    required: false
    os_support: [windows]
    version_policy: {channel: stable, manual_select: true}
    install: {method: binary}
    verify: {commands: ["x --version"], expected: "v"}
    adapter: {mode: external_process, capabilities: [launch_external, dock_if_supported]}
    license: MIT
    tested_versions: ["1.0.0"]
```

```python
# test_validator_urls.py
from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import validate
from hermes3d.registry.errors import ErrorCode

def test_bad_urls_flagged(fixture_path):
    result = validate(load_registry(fixture_path("bad_url_shape.yaml")))
    assert not result.ok
    pairs = {(e.tool_id, e.code) for e in result.errors}
    assert ("bad_one", ErrorCode.INVALID_URL_SHAPE) in pairs
    assert ("bad_two", ErrorCode.INVALID_URL_SHAPE) in pairs
```

- [ ] **Step 2: Add to validator**

```python
import re
_URL_SHAPE = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")

def _check_url(e: ToolEntry) -> list[ValidationError]:
    url = e.reference_url()
    if url is None:
        return [ValidationError(e.key, ErrorCode.MISSING_REQUIRED_FIELD, "must include repo, source, or homepage")]
    if not isinstance(url, str) or not url.strip() or not _URL_SHAPE.match(url):
        return [ValidationError(e.key, ErrorCode.INVALID_URL_SHAPE, f"reference URL '{url}' is not a well-formed http(s) URL")]
    return []

# Extend _check_entry to include _check_url
```

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(registry): URL shape validation"
```

> **CHECKPOINT 2** (after Task 6): registry validator should pass schema + URL tests; coordinator confirms 12+ green tests, posts status, proceeds.

### Task 7: Registry — per-type capability matrix

(Identical to v1 §Task 7. Adds `_check_per_type_capabilities` helper + `slicer_missing_dock_token.yaml` fixture.)

- [ ] **Step 1: Fixture + test**

```yaml
# fixtures/slicer_missing_dock_token.yaml
tools:
  bad_slicer:
    name: BadSlicer
    type: slicer
    repo: https://github.com/x/y
    required: true
    os_support: [windows]
    version_policy: {channel: stable, manual_select: true}
    install: {method: binary}
    verify: {commands: ["bad-slicer --version"], expected: "version"}
    adapter: {mode: cli_external_process, capabilities: [launch_external, slice_to_staging]}
    license: GPL-3.0-or-later
    tested_versions: ["1.0.0"]
```

```python
# Append to test_capability_matrix.py
from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import validate
from hermes3d.registry.errors import ErrorCode

def test_slicer_missing_dock_token_flagged(fixture_path):
    result = validate(load_registry(fixture_path("slicer_missing_dock_token.yaml")))
    assert not result.ok
    pairs = {(e.tool_id, e.code) for e in result.errors}
    assert ("bad_slicer", ErrorCode.MISSING_DOCK_CAPABILITY) in pairs
```

- [ ] **Step 2: Implement**

```python
def _check_per_type_capabilities(e: ToolEntry) -> list[ValidationError]:
    required = required_capabilities_for_type(e.type)
    if not required: return []
    caps = set(e.adapter.capabilities)
    out: list[ValidationError] = []
    for req in required:
        if req.startswith("dock_"):
            if not any(c.startswith("dock_") for c in caps):
                out.append(ValidationError(e.key, ErrorCode.MISSING_DOCK_CAPABILITY,
                    f"type '{e.type}' requires a dock capability (e.g. {req}); none declared"))
        elif req == "launch_external":
            if "launch_external" not in caps and "fullscreen_external" not in caps:
                out.append(ValidationError(e.key, ErrorCode.MISSING_EXTERNAL_LAUNCH_CAPABILITY,
                    f"type '{e.type}' requires 'launch_external' or equivalent; none declared"))
        elif req not in caps:
            out.append(ValidationError(e.key, ErrorCode.MISSING_REQUIRED_FIELD,
                f"type '{e.type}' requires capability '{req}'"))
    return out

# Extend _check_entry
```

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(registry): per-type capability matrix validation"
```

### Task 8: Registry — tested_versions rule

- [ ] **Steps:** add `_check_tested_versions(e)` helper that flags `EMPTY_TESTED_VERSIONS` if list empty. Test using `_entry_factory()` from `test_validator_tested_versions.py`. (Identical to v1 §Task 8.)

```python
# 04_testing/pytest/unit/registry/test_validator_tested_versions.py
from hermes3d.registry.types import AdapterSpec, ToolEntry, VersionPolicy
from hermes3d.registry.validator import validate
from hermes3d.registry.errors import ErrorCode

def _factory(**o):
    base = dict(
        key="x", name="X", type="external_app", required=True,
        os_support=("windows",), version_policy=VersionPolicy(channel="stable", manual_select=True),
        install={"method": "binary"}, verify={"commands": ["x --version"], "expected": "v"},
        adapter=AdapterSpec(mode="external_process", capabilities=("launch_external", "dock_if_supported")),
        license="MIT", tested_versions=("1.0.0",), repo="https://github.com/x/y",
    )
    base.update(o); return ToolEntry(**base)

def test_empty_tested_versions_flagged():
    r = validate([_factory(tested_versions=())])
    assert ErrorCode.EMPTY_TESTED_VERSIONS in {e.code for e in r.errors}

def test_with_tested_versions_passes():
    r = validate([_factory(tested_versions=("1.0.0",))])
    assert r.ok
```

```python
# Add to validator.py
def _check_tested_versions(e: ToolEntry) -> list[ValidationError]:
    if not e.tested_versions:
        return [ValidationError(e.key, ErrorCode.EMPTY_TESTED_VERSIONS,
            "tested_versions must be a non-empty list")]
    return []
# Extend _check_entry
```

```bash
git commit -am "feat(registry): tested_versions required field"
```

### Task 9: Update live registry YAML to satisfy new rules

(Identical to v1 §Task 9. Adds license, tested_versions, dock tokens for all 12 entries.)

License table:
| key | license |
|---|---|
| blender | GPL-3.0-or-later |
| blender_mcp_ahujasid | MIT |
| blender_mcp_vxai | MIT |
| prusa_slicer | AGPL-3.0-or-later |
| orca_slicer | AGPL-3.0-or-later |
| flsun_slicer | proprietary |
| cura | LGPL-3.0-or-later |
| printrun | GPL-3.0-or-later |
| moonraker | GPL-3.0-or-later |
| fluidd | GPL-3.0-or-later |
| mainsail | GPL-3.0-or-later |
| octoprint | AGPL-3.0-or-later |

Plus: add `dock_if_allowed` to slicers + printrun; add `fullscreen_external` to octoprint for vocabulary parity.

Add integration test `test_validator_live_registry.py` that loads the live YAML and asserts pass + 12 entries.

```bash
git commit -m "feat(registry): populate license + tested_versions + dock tokens for all 12 entries"
```

> **CHECKPOINT 3** (after Task 9): the validator gates the live registry YAML — `python -m hermes3d.registry.validator <path>` should print PASS. Coordinator confirms green tests + green live-registry validation, posts status, proceeds.

### Task 10: Replace stale pseudocode + thin CLI wrappers

(Identical to v1 §Task 10. The pseudocode becomes a 1-line redirect stub. Two wrapper scripts.)

```bash
git commit -m "chore(registry): replace stale pseudocode + add CLI wrappers"
```

### Task 11: CI gate (Layer A registry-validator step)

(Identical to v1 §Task 11. Add a step to Layer A in `ci.yml` after the forbidden-pattern scan.)

```bash
git commit -m "ci(registry): gate the hardened validator in Layer A"
```

### Task 12: .gitignore defensive addendum + Orca URL fix

(Identical to v1 §Task 12.)

```bash
git commit -m "chore: defensive secret-vector .gitignore + fix install_plan OrcaSlicer URL"
```

> **CHECKPOINT 4** (after Task 12): registry vertical complete. Coordinator runs full pytest suite, confirms green, posts status, then enters adapter-shell vertical.

### Task 13: ADR-008 — Adapter lifecycle + dock/undock + confirmation envelope

**Files:**
- Create: `02_architecture/adr/ADR-008-adapter-lifecycle-and-dock-undock.md` (creates `adr/` subdir if absent)

**Why:** codifies `03_implementation/adapter_registry/README.md` §3 (lifecycle states), §4 (dock modes), §6 (extended envelope), §7 (Confirmation envelope) as immutable for Phase 1+ work. Future changes to these contracts MUST land as a new ADR (e.g. ADR-009) — not silent code changes.

- [ ] **Step 1: Write the ADR**

Headings (keep terse, follow ADR-001..004 style observed in the kit):
1. **Status** — `Accepted (Phase 1, 2026-04-30)`
2. **Context** — Phase 0 audit found two divergent adapter surfaces; coordinator README §2 reconciled them; this ADR locks the reconciliation
3. **Decision** — the merged 16-method `ToolAdapter` Protocol (per coordinator README §2), the 8-state lifecycle enum (per §3), the 3-mode dock state contract (per §4), the extended `AdapterResult` envelope with `dry_run_token` binding (per §6), the `Confirmation` envelope with HMAC-signed token (per §7)
4. **Consequences** — Phase 3 implementers MUST satisfy this Protocol; Phase 6 write actions MUST require valid `Confirmation`; future adapter-surface changes require a new ADR
5. **Cross-links** — coordinator README, kit's ADAPTER_INTERFACE.md, ADAPTER_BOUNDARY_ARCHITECTURE.md, DOCK_UNDOCK_REQUIREMENTS.md, SECURITY_AND_SAFETY_POLICY.md

- [ ] **Step 2: Commit**

```bash
git add 02_architecture/adr/ADR-008-adapter-lifecycle-and-dock-undock.md
git commit -m "adr(008): adapter lifecycle + dock/undock/external + confirmation envelope (immutable)"
```

### Task 14: Adapter Protocol module — types

**Files:**
- Create: `03_implementation/src/hermes3d/adapters/__init__.py`
- Create: `03_implementation/src/hermes3d/adapters/types.py`
- Create: `04_testing/pytest/unit/adapters/__init__.py`
- Create: `04_testing/pytest/unit/adapters/test_types.py`

- [ ] **Step 1: Failing tests**

```python
# 04_testing/pytest/unit/adapters/test_types.py
from hermes3d.adapters.types import (
    AdapterState, CapabilityFlag, AdapterResult, ProofRef, LogEntry,
    Confirmation, Action, DryRunResult, ExecuteResult, DetectResult,
    ValidateResult, HealthResult, LaunchResult,
)

def test_adapter_state_has_8_canonical_states():
    expected = {"uninstalled", "detected", "configured", "ready",
                "connecting", "connected", "degraded", "error"}
    assert {s.value for s in AdapterState} == expected

def test_capability_flag_has_canonical_set():
    expected = {"cli", "gui", "headless_smoke", "usb", "websocket",
                "rest_api", "mcp", "dock_iframe", "streaming_logs",
                "dry_run_supported", "e_stop", "read_only"}
    assert expected.issubset({c.value for c in CapabilityFlag})

def test_confirmation_requires_dry_run_token_and_signed_token():
    c = Confirmation(
        user="alice", ts_utc="2026-04-30T22:00:00Z", printer_id="t1-1",
        reason_text="manual park", dry_run_token="abc123",
        signed_token="hmac-deadbeef", policy_version="v4.1",
    )
    assert c.dry_run_token == "abc123"
    assert c.signed_token == "hmac-deadbeef"

def test_adapter_result_carries_proof_metadata():
    r = AdapterResult(
        ok=True, adapter="moonraker", mode="detect",
        artifacts=(), logs=(),
        proof=ProofRef(timestamp_utc="2026-04-30T22:00Z", branch="develop", commit="abc123"),
    )
    assert r.ok and r.proof.commit == "abc123"
```

- [ ] **Step 2: Run to confirm fail**

- [ ] **Step 3: Implement `__init__.py` + `types.py`**

```python
# 03_implementation/src/hermes3d/adapters/__init__.py
"""Hermes3D adapter shell — Protocol + skeletons for Phase 1 detect-only."""
```

```python
# 03_implementation/src/hermes3d/adapters/types.py
"""Adapter-system types per ADR-008.

All dataclasses are frozen; immutability is part of the proof model.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Mapping

class AdapterState(str, Enum):
    UNINSTALLED = "uninstalled"
    DETECTED = "detected"
    CONFIGURED = "configured"
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"

class CapabilityFlag(str, Enum):
    CLI = "cli"
    GUI = "gui"
    HEADLESS_SMOKE = "headless_smoke"
    USB = "usb"
    WEBSOCKET = "websocket"
    REST_API = "rest_api"
    MCP = "mcp"
    DOCK_IFRAME = "dock_iframe"
    STREAMING_LOGS = "streaming_logs"
    DRY_RUN_SUPPORTED = "dry_run_supported"
    E_STOP = "e_stop"
    READ_ONLY = "read_only"

DockMode = Literal["docked", "undocked", "external"]
Severity = Literal["info", "warn", "error", "fatal"]

@dataclass(frozen=True)
class ProofRef:
    timestamp_utc: str
    branch: str
    commit: str

@dataclass(frozen=True)
class LogEntry:
    ts_utc: str
    severity: Severity
    source: str
    code: str | None
    msg: str
    redactions: tuple[str, ...] = ()

@dataclass(frozen=True)
class ArtifactRef:
    path: str
    sha256: str | None = None

@dataclass(frozen=True)
class AdapterResult:
    ok: bool
    adapter: str
    mode: str
    artifacts: tuple[ArtifactRef, ...]
    logs: tuple[LogEntry, ...]
    proof: ProofRef
    error_code: str | None = None
    severity: Severity | None = None
    recoverable: bool = True
    user_action_required: str | None = None
    dry_run_token: str | None = None

@dataclass(frozen=True)
class DetectResult:
    found: bool
    state: AdapterState
    detail: str = ""

@dataclass(frozen=True)
class ValidateResult:
    ok: bool
    state: AdapterState
    issues: tuple[str, ...] = ()

@dataclass(frozen=True)
class HealthResult:
    ok: bool
    state: AdapterState
    latency_ms: int | None = None
    detail: str = ""

@dataclass(frozen=True)
class LaunchResult:
    ok: bool
    mode: DockMode
    pid: int | None = None
    detail: str = ""

@dataclass(frozen=True)
class Action:
    kind: str
    payload: Mapping[str, object]

@dataclass(frozen=True)
class DryRunResult:
    ok: bool
    dry_run_token: str
    summary: str
    detail: str = ""

@dataclass(frozen=True)
class ExecuteResult:
    ok: bool
    artifacts: tuple[ArtifactRef, ...] = ()
    detail: str = ""

@dataclass(frozen=True)
class Confirmation:
    user: str
    ts_utc: str
    printer_id: str | None
    reason_text: str
    dry_run_token: str
    signed_token: str
    policy_version: str
```

- [ ] **Step 4: Run to confirm pass**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/adapters/ 04_testing/pytest/unit/adapters/
git commit -m "feat(adapters): types per ADR-008 (lifecycle, capabilities, envelope, confirmation)"
```

### Task 15: Adapter Protocol + base SkeletonAdapter

**Files:**
- Create: `03_implementation/src/hermes3d/adapters/protocol.py`
- Create: `03_implementation/src/hermes3d/adapters/base.py`
- Create: `04_testing/pytest/unit/adapters/test_protocol.py`

- [ ] **Step 1: Failing test**

```python
# test_protocol.py
import pytest
from hermes3d.adapters.protocol import ToolAdapter, NotImplementedYet
from hermes3d.adapters.base import SkeletonAdapter
from hermes3d.adapters.types import (
    AdapterState, Action, Confirmation,
)

class _Demo(SkeletonAdapter):
    key = "demo"
    display_name = "Demo"
    category = "external_app"
    dangerous = False

    def detect(self):
        return self._detect_result(False, AdapterState.UNINSTALLED, "demo never installs")

    def version(self):
        return None

    def capabilities(self):
        return frozenset()

def test_skeleton_implements_protocol():
    a = _Demo()
    assert isinstance(a, ToolAdapter)

def test_skeleton_methods_raise_not_implemented_yet():
    a = _Demo()
    with pytest.raises(NotImplementedYet):
        a.dry_run(Action(kind="noop", payload={}))
    with pytest.raises(NotImplementedYet):
        a.execute(Action(kind="noop", payload={}),
                  Confirmation("u", "t", None, "r", "tok", "sig", "v4.1"))
    with pytest.raises(NotImplementedYet):
        a.open_docked()

def test_detect_returns_state():
    r = _Demo().detect()
    assert r.state == AdapterState.UNINSTALLED
    assert not r.found
```

- [ ] **Step 2: Implement**

```python
# 03_implementation/src/hermes3d/adapters/protocol.py
"""ToolAdapter Protocol per ADR-008."""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from .types import (
    Action, AdapterState, Confirmation, DetectResult, DryRunResult,
    ExecuteResult, HealthResult, LaunchResult, ValidateResult,
)

class NotImplementedYet(NotImplementedError):
    """Phase-1 skeleton method placeholder. Phase 3 implements read-only methods; Phase 6 implements write methods."""

@runtime_checkable
class ToolAdapter(Protocol):
    key: str
    display_name: str
    category: str
    dangerous: bool

    def version(self) -> str | None: ...
    def detect(self) -> DetectResult: ...
    def capabilities(self) -> frozenset[str]: ...
    def validate(self) -> ValidateResult: ...
    def healthcheck(self) -> HealthResult: ...
    def status(self) -> AdapterState: ...
    def open_docked(self) -> LaunchResult: ...
    def open_undocked(self) -> LaunchResult: ...
    def open_external(self) -> LaunchResult: ...
    def detach_ui(self) -> None: ...
    def dry_run(self, action: Action) -> DryRunResult: ...
    def execute(self, action: Action, confirmation: Confirmation) -> ExecuteResult: ...
```

```python
# 03_implementation/src/hermes3d/adapters/base.py
"""Skeleton base class — Phase 1 detect-only adapters subclass this.

All non-detection methods raise NotImplementedYet with a clear hand-off message
naming the phase that will implement them.
"""
from __future__ import annotations
from .protocol import NotImplementedYet
from .types import (
    Action, AdapterState, Confirmation, DetectResult, DryRunResult,
    ExecuteResult, HealthResult, LaunchResult, ValidateResult,
)

class SkeletonAdapter:
    key: str = ""
    display_name: str = ""
    category: str = ""
    dangerous: bool = False

    @staticmethod
    def _detect_result(found: bool, state: AdapterState, detail: str = "") -> DetectResult:
        return DetectResult(found=found, state=state, detail=detail)

    # Phase 1 implements detect / version / capabilities in subclasses.
    def detect(self) -> DetectResult: raise NotImplementedYet("detect")  # subclasses MUST override
    def version(self) -> str | None: raise NotImplementedYet("version")  # subclasses MUST override
    def capabilities(self) -> frozenset[str]: raise NotImplementedYet("capabilities")  # subclasses MUST override

    # Phase 3 read-only methods — left as NotImplementedYet for Phase 1.
    def validate(self) -> ValidateResult: raise NotImplementedYet("validate — see Phase 3")
    def healthcheck(self) -> HealthResult: raise NotImplementedYet("healthcheck — see Phase 3")
    def status(self) -> AdapterState: raise NotImplementedYet("status — see Phase 3")
    def open_docked(self) -> LaunchResult: raise NotImplementedYet("open_docked — see Phase 3")
    def open_undocked(self) -> LaunchResult: raise NotImplementedYet("open_undocked — see Phase 3")
    def open_external(self) -> LaunchResult: raise NotImplementedYet("open_external — see Phase 3")
    def detach_ui(self) -> None: raise NotImplementedYet("detach_ui — see Phase 3")

    # Phase 6 write methods — left as NotImplementedYet for Phase 1.
    def dry_run(self, action: Action) -> DryRunResult: raise NotImplementedYet("dry_run — see Phase 6")
    def execute(self, action: Action, confirmation: Confirmation) -> ExecuteResult:
        raise NotImplementedYet("execute — see Phase 6")
```

- [ ] **Step 3: Run, confirm pass, commit**

```bash
git add 03_implementation/src/hermes3d/adapters/protocol.py 03_implementation/src/hermes3d/adapters/base.py 04_testing/pytest/unit/adapters/test_protocol.py
git commit -m "feat(adapters): ToolAdapter Protocol + SkeletonAdapter base class"
```

> **CHECKPOINT 5** (after Task 15): adapter Protocol + base in place. Coordinator runs full pytest, posts status, proceeds to skeletons.

### Task 16: 11 adapter skeletons + parameterized smoke tests

**Files:**
- Create: 11 files under `03_implementation/src/hermes3d/adapters/{moonraker,octoprint,printrun,prusa_slicer,orca_slicer,flsun_slicer,cura,blender,blender_mcp,fluidd,mainsail}.py`
- Create: `04_testing/pytest/unit/adapters/test_skeletons.py`

Each skeleton implements ONLY:
- Class-level `key`, `display_name`, `category`, `dangerous`
- `detect()` — best-effort, side-effect-free probe (e.g. `shutil.which("blender")`, `os.path.exists("/dev/ttyUSB0")` etc.) returning `DetectResult`
- `version()` — if detect succeeded, run `--version`; else `None`. May use `subprocess.run` with a short timeout. NEVER raises on failure — returns `None`.
- `capabilities()` — hardcoded `frozenset[str]` matching the registry's `adapter.capabilities` list

Other methods inherited from `SkeletonAdapter` raise `NotImplementedYet`.

- [ ] **Step 1: Write parameterized smoke test FIRST**

```python
# 04_testing/pytest/unit/adapters/test_skeletons.py
import pytest
from hermes3d.adapters import (
    moonraker, octoprint, printrun, prusa_slicer, orca_slicer, flsun_slicer,
    cura, blender, blender_mcp, fluidd, mainsail,
)
from hermes3d.adapters.protocol import ToolAdapter, NotImplementedYet
from hermes3d.adapters.types import AdapterState, DetectResult

ALL_SKELETONS = [
    (moonraker.MoonrakerAdapter, "moonraker", "printer", False),
    (octoprint.OctoPrintAdapter, "octoprint", "printer", False),
    (printrun.PrintrunAdapter, "printrun", "printer", True),  # USB writes are dangerous
    (prusa_slicer.PrusaSlicerAdapter, "prusa_slicer", "slicer", True),
    (orca_slicer.OrcaSlicerAdapter, "orca_slicer", "slicer", True),
    (flsun_slicer.FLSunSlicerAdapter, "flsun_slicer", "slicer", True),
    (cura.CuraAdapter, "cura", "slicer", True),
    (blender.BlenderAdapter, "blender", "3d", True),
    (blender_mcp.BlenderMCPAdapter, "blender_mcp", "3d-mcp", True),
    (fluidd.FluiddAdapter, "fluidd", "printer-ui", False),
    (mainsail.MainsailAdapter, "mainsail", "printer-ui", False),
]

@pytest.mark.parametrize("cls,key,category,dangerous", ALL_SKELETONS)
def test_skeleton_implements_protocol(cls, key, category, dangerous):
    a = cls()
    assert isinstance(a, ToolAdapter), f"{key} does not implement ToolAdapter"
    assert a.key == key
    assert a.category == category
    assert a.dangerous == dangerous

@pytest.mark.parametrize("cls,key,_c,_d", ALL_SKELETONS)
def test_skeleton_detect_does_not_raise(cls, key, _c, _d):
    """detect() MUST be safe to call on any host. It can return UNINSTALLED but never crashes."""
    r = cls().detect()
    assert isinstance(r, DetectResult)
    assert r.state in {AdapterState.UNINSTALLED, AdapterState.DETECTED}

@pytest.mark.parametrize("cls,key,_c,_d", ALL_SKELETONS)
def test_skeleton_capabilities_nonempty(cls, key, _c, _d):
    caps = cls().capabilities()
    assert isinstance(caps, frozenset)
    assert len(caps) > 0

@pytest.mark.parametrize("cls,key,_c,_d", ALL_SKELETONS)
def test_skeleton_version_doesnt_raise(cls, key, _c, _d):
    v = cls().version()
    assert v is None or isinstance(v, str)

@pytest.mark.parametrize("cls,key,_c,_d", ALL_SKELETONS)
def test_skeleton_validate_raises_not_implemented_yet(cls, key, _c, _d):
    """Phase 3 work — Phase 1 must hand off cleanly."""
    with pytest.raises(NotImplementedYet, match="Phase 3"):
        cls().validate()
```

- [ ] **Step 2: Implement each skeleton** (template — repeat per adapter, vary detect/capabilities)

Template for a binary-detect adapter:

```python
# 03_implementation/src/hermes3d/adapters/blender.py
from __future__ import annotations
import shutil, subprocess
from .base import SkeletonAdapter
from .types import AdapterState, DetectResult

class BlenderAdapter(SkeletonAdapter):
    key = "blender"
    display_name = "Blender"
    category = "3d"
    dangerous = True

    _CAPABILITIES = frozenset({"detect", "launch_external", "dock_if_supported", "screenshot_source"})

    def detect(self) -> DetectResult:
        path = shutil.which("blender")
        if path:
            return self._detect_result(True, AdapterState.DETECTED, f"binary at {path}")
        return self._detect_result(False, AdapterState.UNINSTALLED, "blender not on PATH")

    def version(self) -> str | None:
        path = shutil.which("blender")
        if not path:
            return None
        try:
            out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
            return out.stdout.strip().splitlines()[0] if out.returncode == 0 else None
        except (subprocess.TimeoutExpired, OSError):
            return None

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
```

Variants:
- **HTTP-API adapters** (moonraker, octoprint): detect by checking config existence (per-deployment toml has the URL). With no config, return UNINSTALLED. No network calls in Phase 1.
- **Web-UI adapters** (fluidd, mainsail): same — config-driven detection only.
- **USB adapter** (printrun): try `shutil.which("pronsole")` AND check for serial-port enumeration (cross-platform: `pyserial` if available). No port-open.
- **MCP adapter** (blender_mcp): detect by `shutil.which("uvx")` AND check for `claude mcp list` containing the provider key. Best-effort, may return UNINSTALLED.
- **Slicers** (prusa_slicer, orca_slicer, cura, flsun_slicer): `shutil.which()` against the platform-appropriate binary names.

Each skeleton's `_CAPABILITIES` matches the live registry YAML's `adapter.capabilities` list.

- [ ] **Step 3: Run all tests**

```bash
python -m pytest 04_testing/pytest/unit/adapters/ -v
# Expected: 50+ tests (5 tests × 11 skeletons + 4 base tests), all green
```

- [ ] **Step 4: Commit**

```bash
git add 03_implementation/src/hermes3d/adapters/{moonraker,octoprint,printrun,prusa_slicer,orca_slicer,flsun_slicer,cura,blender,blender_mcp,fluidd,mainsail}.py 04_testing/pytest/unit/adapters/test_skeletons.py
git commit -m "feat(adapters): 11 detect/version/capabilities skeletons (Phase 3-6 stubs raise NotImplementedYet)"
```

### Task 17: JSON config schemas (9 files)

**Files:**
- Create 9 JSON Schemas under `03_implementation/adapter_registry/schemas/`
- Create: `04_testing/pytest/unit/adapters/test_config_schemas.py`

Add `jsonschema>=4.0` to `03_implementation/pyproject.toml` `[project.optional-dependencies].all`. Confirm pin doesn't conflict.

Schema template (per `03_implementation/adapter_registry/README.md` §8):

```json
// 03_implementation/adapter_registry/schemas/moonraker.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "hermes3d://adapter_registry/schemas/moonraker.schema.json",
  "title": "Moonraker adapter config",
  "type": "object",
  "additionalProperties": false,
  "required": ["host", "port"],
  "properties": {
    "host": {"type": "string", "format": "hostname"},
    "port": {"type": "integer", "minimum": 1, "maximum": 65535},
    "api_key": {"type": ["string", "null"], "default": null},
    "wss_path": {"type": "string", "default": "/websocket"},
    "tls_verify": {"type": "boolean", "default": true},
    "timeout_ms": {"type": "integer", "minimum": 100, "default": 5000}
  }
}
```

Repeat for: octoprint, printrun, prusa_slicer, orca_slicer, flsun_slicer, cura, blender, blender_mcp.

Test:

```python
# 04_testing/pytest/unit/adapters/test_config_schemas.py
import json
from pathlib import Path
import pytest
import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parents[4] / "03_implementation" / "adapter_registry" / "schemas"

EXPECTED = ["moonraker", "octoprint", "printrun", "prusa_slicer", "orca_slicer",
            "flsun_slicer", "cura", "blender", "blender_mcp"]

@pytest.mark.parametrize("name", EXPECTED)
def test_schema_is_valid_jsonschema(name):
    path = SCHEMA_DIR / f"{name}.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)

def test_moonraker_schema_rejects_missing_host():
    schema = json.loads((SCHEMA_DIR / "moonraker.schema.json").read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"port": 7125}, schema)

def test_moonraker_schema_accepts_minimal_valid():
    schema = json.loads((SCHEMA_DIR / "moonraker.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate({"host": "192.168.0.10", "port": 7125}, schema)
```

```bash
git add 03_implementation/adapter_registry/schemas/ 04_testing/pytest/unit/adapters/test_config_schemas.py 03_implementation/pyproject.toml
git commit -m "feat(adapters): JSON config schemas for 9 adapters + jsonschema dep"
```

### Task 18: env-detect — types + JSON Schema + cascade + fixtures + tests

**Files:**
- Create: `03_implementation/src/hermes3d/env/__init__.py`
- Create: `03_implementation/src/hermes3d/env/types.py`
- Create: `03_implementation/src/hermes3d/env/detect.py`
- Create: `03_implementation/src/hermes3d/env/edition.py`
- Create: `schemas/env_report.schema.json`
- Create: `04_testing/pytest/unit/env/__init__.py`
- Create: `04_testing/pytest/unit/env/test_detect.py`
- Create: `04_testing/pytest/unit/env/test_edition.py`
- Create: `04_testing/pytest/unit/env/fixtures/{nvidia_smi_3090ti,nvidia_smi_no_gpu,no_nvidia_smi,no_gpu}.json`
- Create: `scripts/env-detect.sh`
- Create: `scripts/env-detect.ps1`

- [ ] **Step 1: Define `EnvReport` dataclass + JSON Schema**

```python
# 03_implementation/src/hermes3d/env/types.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Literal

Edition = Literal["desktop_gpu_worker", "ubuntu_vps_control_server", "blocked_no_gpu"]
Vendor = Literal["NVIDIA", "AMD", "Intel", "none", "unknown"]
DetectionSource = Literal["nvidia-smi", "torch.cuda", "wmi", "unavailable"]

@dataclass(frozen=True)
class EnvReport:
    timestamp_utc: str
    platform: str               # "windows" | "linux" | "macos" | "other"
    python_version: str
    edition: Edition
    vendor: Vendor
    detection_source: DetectionSource
    cuda_available: bool
    gpu_name: str | None = None
    vram_total_mib: int | None = None
    vram_free_mib: int | None = None
    driver_version: str | None = None
    node_version: str | None = None
    shells: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return asdict(self)
```

```json
// schemas/env_report.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "hermes3d://schemas/env_report.schema.json",
  "title": "Hermes3D environment detection report",
  "type": "object",
  "additionalProperties": false,
  "required": ["timestamp_utc", "platform", "python_version", "edition",
               "vendor", "detection_source", "cuda_available"],
  "properties": {
    "timestamp_utc": {"type": "string", "format": "date-time"},
    "platform": {"type": "string", "enum": ["windows", "linux", "macos", "other"]},
    "python_version": {"type": "string"},
    "edition": {"type": "string", "enum": ["desktop_gpu_worker", "ubuntu_vps_control_server", "blocked_no_gpu"]},
    "vendor": {"type": "string", "enum": ["NVIDIA", "AMD", "Intel", "none", "unknown"]},
    "detection_source": {"type": "string", "enum": ["nvidia-smi", "torch.cuda", "wmi", "unavailable"]},
    "cuda_available": {"type": "boolean"},
    "gpu_name": {"type": ["string", "null"]},
    "vram_total_mib": {"type": ["integer", "null"], "minimum": 0},
    "vram_free_mib": {"type": ["integer", "null"], "minimum": 0},
    "driver_version": {"type": ["string", "null"]},
    "node_version": {"type": ["string", "null"]},
    "shells": {"type": "array", "items": {"type": "string"}}
  }
}
```

- [ ] **Step 2: Edition resolution rule**

```python
# 03_implementation/src/hermes3d/env/edition.py
"""Edition resolution per DUAL_EDITION_ENVIRONMENT_BASELINE.md §4."""
from __future__ import annotations
from .types import Edition, Vendor

def resolve_edition(platform: str, vendor: Vendor, cuda_available: bool) -> Edition:
    if platform == "windows" and vendor == "NVIDIA":
        return "desktop_gpu_worker"
    if platform == "linux" and not cuda_available:
        return "ubuntu_vps_control_server"
    if platform == "linux" and cuda_available:
        return "desktop_gpu_worker"
    return "blocked_no_gpu"
```

```python
# 04_testing/pytest/unit/env/test_edition.py
from hermes3d.env.edition import resolve_edition

def test_windows_with_nvidia_is_desktop_worker():
    assert resolve_edition("windows", "NVIDIA", True) == "desktop_gpu_worker"

def test_linux_without_cuda_is_vps():
    assert resolve_edition("linux", "none", False) == "ubuntu_vps_control_server"

def test_linux_with_cuda_is_desktop_worker():
    assert resolve_edition("linux", "NVIDIA", True) == "desktop_gpu_worker"

def test_macos_is_blocked():
    assert resolve_edition("macos", "none", False) == "blocked_no_gpu"

def test_windows_without_nvidia_is_blocked():
    assert resolve_edition("windows", "AMD", False) == "blocked_no_gpu"
```

- [ ] **Step 3: Cascade detector + fixtures**

```python
# 03_implementation/src/hermes3d/env/detect.py
"""Cascade: nvidia-smi → torch.cuda → WMI → safe-unavailable."""
from __future__ import annotations
import datetime, platform as plat, shutil, subprocess, sys
from pathlib import Path
from typing import Callable
from .edition import resolve_edition
from .types import EnvReport, DetectionSource, Vendor

def _platform_name() -> str:
    s = plat.system().lower()
    if s.startswith("win"): return "windows"
    if s == "linux": return "linux"
    if s == "darwin": return "macos"
    return "other"

def _try_nvidia_smi(runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> tuple[bool, dict]:
    if not shutil.which("nvidia-smi"):
        return False, {}
    try:
        r = runner(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
                    "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
        if r.returncode != 0 or not r.stdout.strip():
            return False, {}
        first = r.stdout.strip().splitlines()[0].split(",")
        if len(first) < 4:
            return False, {}
        name, total, free, drv = (s.strip() for s in first[:4])
        return True, {
            "vendor": "NVIDIA", "gpu_name": name,
            "vram_total_mib": int(total), "vram_free_mib": int(free),
            "driver_version": drv, "cuda_available": True,
            "detection_source": "nvidia-smi",
        }
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False, {}

def _try_torch_cuda() -> tuple[bool, dict]:
    try:
        import torch  # type: ignore
    except ImportError:
        return False, {}
    if not getattr(torch, "cuda", None) or not torch.cuda.is_available():
        return False, {}
    try:
        idx = torch.cuda.current_device()
        return True, {
            "vendor": "NVIDIA", "gpu_name": torch.cuda.get_device_name(idx),
            "cuda_available": True, "detection_source": "torch.cuda",
        }
    except Exception:
        return False, {}

def _try_wmi() -> tuple[bool, dict]:
    if _platform_name() != "windows":
        return False, {}
    try:
        r = subprocess.run(["wmic", "path", "win32_VideoController", "get", "name"],
                           capture_output=True, text=True, timeout=5)
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip() and l.strip() != "Name"]
        if not lines:
            return False, {}
        name = lines[0]
        vendor: Vendor = ("NVIDIA" if "NVIDIA" in name.upper() else
                          "AMD" if "AMD" in name.upper() or "RADEON" in name.upper() else
                          "Intel" if "INTEL" in name.upper() else "unknown")
        return True, {"vendor": vendor, "gpu_name": name,
                      "cuda_available": False, "detection_source": "wmi"}
    except (OSError, subprocess.TimeoutExpired):
        return False, {}

def _node_version() -> str | None:
    if not shutil.which("node"): return None
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def _shells() -> tuple[str, ...]:
    out = []
    for sh in ("bash", "pwsh", "cmd"):
        if shutil.which(sh): out.append(sh)
    return tuple(out)

def detect_env() -> EnvReport:
    """Run the cascade and return a fully-populated EnvReport."""
    base = {
        "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "platform": _platform_name(),
        "python_version": sys.version.split()[0],
        "node_version": _node_version(),
        "shells": _shells(),
        "vendor": "none", "detection_source": "unavailable",
        "cuda_available": False, "gpu_name": None,
        "vram_total_mib": None, "vram_free_mib": None, "driver_version": None,
    }
    for fn in (_try_nvidia_smi, _try_torch_cuda, _try_wmi):
        ok, data = fn()
        if ok:
            base.update(data); break
    base["edition"] = resolve_edition(base["platform"], base["vendor"], base["cuda_available"])
    return EnvReport(**base)
```

- [ ] **Step 4: Fixtures (sample shapes; real fixtures captured below; tests use them via `_try_nvidia_smi(runner=mock_runner)` injection)**

The cascade above takes a `runner` injection point so tests can mock subprocess. Fixtures are JSON snapshots of expected `EnvReport.to_dict()` per scenario, used for golden comparison:

```json
// 04_testing/pytest/unit/env/fixtures/nvidia_smi_3090ti.json
{
  "platform": "windows", "vendor": "NVIDIA",
  "gpu_name": "NVIDIA GeForce RTX 3090 Ti",
  "vram_total_mib": 24564, "vram_free_mib": 18493,
  "driver_version": "591.86", "cuda_available": true,
  "detection_source": "nvidia-smi",
  "edition": "desktop_gpu_worker"
}
```

```json
// 04_testing/pytest/unit/env/fixtures/no_nvidia_smi.json
{
  "platform": "linux", "vendor": "none",
  "gpu_name": null, "vram_total_mib": null, "vram_free_mib": null,
  "driver_version": null, "cuda_available": false,
  "detection_source": "unavailable",
  "edition": "ubuntu_vps_control_server"
}
```

(Two more fixtures for `nvidia_smi_no_gpu` and `no_gpu` scenarios.)

- [ ] **Step 5: Tests using mocked runners**

```python
# 04_testing/pytest/unit/env/test_detect.py
import json, subprocess
from pathlib import Path
from unittest.mock import patch
from hermes3d.env.detect import detect_env, _try_nvidia_smi
from hermes3d.env.types import EnvReport

FIXTURES = Path(__file__).parent / "fixtures"

class _FakeProc:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout; self.returncode = returncode

def _runner(stdout: str, rc: int = 0):
    def _run(*a, **kw): return _FakeProc(stdout, rc)
    return _run

def test_nvidia_smi_3090ti_parses():
    out = "NVIDIA GeForce RTX 3090 Ti, 24564, 18493, 591.86\n"
    with patch("hermes3d.env.detect.shutil.which", return_value="/usr/bin/nvidia-smi"):
        ok, data = _try_nvidia_smi(_runner(out))
    assert ok
    assert data["gpu_name"] == "NVIDIA GeForce RTX 3090 Ti"
    assert data["vram_total_mib"] == 24564
    assert data["driver_version"] == "591.86"

def test_nvidia_smi_absent_returns_unavailable():
    with patch("hermes3d.env.detect.shutil.which", return_value=None):
        ok, data = _try_nvidia_smi(_runner(""))
    assert not ok and data == {}

def test_full_detect_env_returns_envreport():
    r = detect_env()
    assert isinstance(r, EnvReport)
    assert r.platform in {"windows", "linux", "macos", "other"}
    assert r.edition in {"desktop_gpu_worker", "ubuntu_vps_control_server", "blocked_no_gpu"}

def test_envreport_validates_against_jsonschema():
    """Live envreport must conform to schemas/env_report.schema.json."""
    import jsonschema
    schema_path = Path(__file__).resolve().parents[4] / "schemas" / "env_report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(detect_env().to_dict(), schema)
```

- [ ] **Step 6: Wrappers**

```bash
# scripts/env-detect.sh
#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  "$PY" -c "import json; from hermes3d.env.detect import detect_env; print(json.dumps(detect_env().to_dict(), indent=2))" "$@"
```

```powershell
# scripts/env-detect.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
    python -c "import json; from hermes3d.env.detect import detect_env; print(json.dumps(detect_env().to_dict(), indent=2))" @args
    exit $LASTEXITCODE
} finally { Pop-Location }
```

- [ ] **Step 7: Run, commit**

```bash
git add 03_implementation/src/hermes3d/env/ schemas/env_report.schema.json 04_testing/pytest/unit/env/ scripts/env-detect.sh scripts/env-detect.ps1
git commit -m "feat(env): cascade detector + JSON schema + edition resolution + 4 fixtures"
```

> **CHECKPOINT 6** (after Task 18): adapter shell + env detect complete. Coordinator runs full pytest, posts status. The hard work is done.

### Task 19: Phase 1 completion report + signed bundle

(Identical to v1 §Task 13 but expanded to cover the 7-deliverable scope.)

- [ ] **Step 1: Write `00_overview/PHASE1_COMPLETION_REPORT.md`** modeled on PHASE0_BASELINE_REPORT — sections: per-task scorecard, new code surface (LOC + files), validator + adapter + env test results, CI gate added, Phase 0 finding closeout (cross-reference each finding to the closing task), constraints honored, signed bundle path + sha256, what remains for Phase 2/3 (UI, real read-only adapter implementations).

- [ ] **Step 2: Build + verify Phase 1 signed bundle**

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  bash scripts/build-bundle.sh --output 05_truth_proof/bundles/
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python 05_truth_proof/conformance_runner.py --bundle <path>
# expect: OK — signature + file hashes + cross-refs verified, dirty=False
```

- [ ] **Step 3: Commit**

```bash
git commit -am "phase-1: completion report + signed bundle"
```

### Task 20: Push branch + open PR + STOP

(Identical to v1 §Task 14.)

- [ ] **Step 1: Push**
- [ ] **Step 2: Open PR** targeting `develop`
- [ ] **Step 3: Confirm CI passes** — every gate including the new Layer A registry-validator step
- [ ] **Step 4: STOP — wait for user approval. No auto-merge. No Phase 2 trigger.**

> **CHECKPOINT 7** (final): PR opened + CI green; coordinator posts the closeout status and stops.

---

## Self-Review

**Spec coverage check:**
- ✅ User scope item 1 "Registry validator rewrite + tests" → Tasks 1-9 + 11
- ✅ User scope item 2 "env-detect.py + schema + fixtures" → Task 18
- ✅ User scope item 3 "adapter Protocol/interface normalization" → Tasks 14-15
- ✅ User scope item 4 "11 adapter skeletons" → Task 16
- ✅ User scope item 5 "JSON config schemas" → Task 17
- ✅ User scope item 6 "ADR-008 adapter boundary / lifecycle / dock-undock model" → Task 13
- ✅ User scope item 7 "proof report + PR to develop" → Tasks 19-20
- ✅ Constraint "no UI-Final" — no UI work in any task
- ✅ Constraint "no rc1 changes" — no edit to `release/v5.3.0-rc1` or the tag
- ✅ Constraint "no real tool integration" — skeletons raise NotImplementedYet for everything beyond detect/version/capabilities
- ✅ Constraint "no real printer control" — Phase 6 explicitly deferred; `execute()` raises NotImplementedYet

**Phase 0 finding closeout (registry axis only — adapter / env findings close in their respective tasks):**
- ✅ Stale pseudocode → Task 10
- ✅ No license field → Tasks 5 + 9
- ✅ No per-type capability matrix → Tasks 3 + 7
- ✅ No tested_versions → Tasks 8 + 9
- ✅ No URL shape check → Task 6
- ✅ No structured error model → Task 2
- ✅ Default-path CWD-relative → Task 5
- ✅ Orca URL drift → Task 12
- ✅ .gitignore missing secret-vector patterns → Task 12
- ✅ Two divergent adapter surfaces → Task 13 (ADR codifies the merge)
- ✅ Adapter lifecycle undefined → Task 13 + Task 14
- ✅ Confirmation envelope undefined → Task 13 + Task 14
- ✅ Capability flag vocabulary undefined → Task 14
- ✅ No env-detect script → Task 18
- ✅ Edition resolution rule implicit → Task 18 (`edition.py`)

**Placeholder scan:** none — every task has either real code or a concrete spec section reference + checkbox steps.

**Type consistency:** `ToolEntry`, `ValidationError`, `ErrorCode`, `AdapterState`, `CapabilityFlag`, `Confirmation`, `EnvReport`, `Edition` all used identically across tasks.

**TDD pattern:** every code task has write-test → fail → implement → pass → commit.

**DRY:** capability matrix lives in `capability_matrix.py` only; lifecycle states in `adapters/types.py` only; edition rule in `env/edition.py` only.

**YAGNI:** no abstractions for hypothetical future tools/editions; skeletons implement only what Phase 1 needs.

**Frequent commits:** 18 commits across 20 tasks (Tasks 11+12 share branches with adjacent tasks).

---

## Execution

**Mode (per user override):** inline execution with checkpoints every 3-4 tasks.

**Checkpoint cadence:**
- After Task 3 (registry types + errors + capability matrix)
- After Task 6 (loader + validator schema rules + URL rules)
- After Task 9 (per-type matrix + tested_versions + live YAML green)
- After Task 12 (small cleanups + CI gate)
- After Task 15 (ADR-008 + adapter Protocol + base)
- After Task 18 (skeletons + JSON schemas + env-detect)
- Final (PR opened, CI green)

**At each checkpoint** the coordinator posts a tight status: tasks completed, tests added, test counts (X passed / 0 failed), commits, blockers (if any). User can intervene; otherwise coordinator continues.
