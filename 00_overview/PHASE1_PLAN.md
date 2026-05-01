# Phase 1 Implementation Plan — Registry + Validators

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the kit-shipped registry validator from a self-contained `scripts/validate_registry.py` baseline into a hardened, typed, importable Python package under `src/hermes3d/registry/`, close the schema gaps the Phase 0 audit identified (license, per-type capability matrix, tested_versions, URL shape), populate the new fields in the live registry YAML, and gate the validator in CI.

**Architecture:** Pure-Python, no new runtime deps beyond `PyYAML` (already present). Two layers: (1) a thin `loader` that parses the YAML into typed dataclasses; (2) a `validator` that runs structural + semantic + per-type rules and returns a structured `ValidationResult`. The kit's existing `scripts/validate_registry.py` stays in place as a minimum-baseline check; the production validator is added under `src/` and exposed via a new `scripts/validate-registry.sh` wrapper. The stale `registry_validator_pseudocode.py` is replaced with a one-line redirect stub so it can no longer mislead implementers. Tests live under `04_testing/pytest/unit/registry/` with fixture YAMLs covering happy-path + every error class.

**Tech Stack:** Python 3.11+, PyYAML, pytest, ruff (existing pins). No new dependencies. Targets Layer B in CI.

---

## Scope

**In scope (this PR):**
1. Real registry validator under `src/hermes3d/registry/` (loader + validator + types + errors)
2. Hardened schema rules: license field, per-`type` capability matrix, tested_versions, URL shape
3. Update `hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml` to populate the new required fields on all 12 entries
4. Replace `hermes3d_gui_contract_kit_v4.1/scripts/registry_validator_pseudocode.py` with a one-line stub redirecting to the real validator
5. Thin CLI wrapper at `scripts/validate-registry.sh` (+ `.ps1`) calling into the new package
6. Pytest unit + integration tests for loader + validator (golden YAML + bad fixtures)
7. CI gating — extend Layer A or add a sub-step that runs `python -m hermes3d.registry.validator` against the live registry YAML
8. `.gitignore` defensive addendum — `*.pem`, `*.key`, `id_rsa*`, `*.p12`, `*.pfx`
9. Fix `install_plan.md` Orca URL drift (registry has correct `SoftFever/OrcaSlicer`; install_plan says `OrcaSlicer/OrcaSlicer`)
10. Phase 1 completion report at `00_overview/PHASE1_COMPLETION_REPORT.md` + signed Phase 1 proof bundle

**Explicitly NOT in scope (deferred to later phases per kit):**
- `scripts/env-detect.py` and `schemas/env_report.schema.json` — kit places this in Phase 4 (Windows GPU Worker); it can be advanced into a Phase 3 follow-up if the user requests
- Adapter shell skeletons + JSON config schemas — kit Phase 3 ("read-only tool detection adapters")
- ADR-005/006/007 (threat model, edition rule, worker auth) — land in Phase 4 / 5 when tunnel + worker code is imminent
- ADR-008 (adapter lifecycle + confirmation envelope) — codifies `03_implementation/adapter_registry/README.md` §3 + §7; lands when the adapter shell does (Phase 3)
- `02_architecture/AUDIT_LOG_SCHEMA.md` and `RATE_LIMIT_POLICY.md` — Phase 4 / 5

> **If the user wants to expand Phase 1 to include env-detect + adapter shell + ADR-008**, this plan stays the same for items 1-10 but appends three additional task groups (Tasks E1-E3 below the main plan, currently marked as "deferred — do not execute unless user expands scope").

---

## File Structure

```
03_implementation/src/hermes3d/registry/
├── __init__.py                       (1 line: package marker + version)
├── types.py                          (dataclasses: ToolEntry, AdapterSpec, VersionPolicy, etc.)
├── loader.py                         (YAML → typed entries; raises LoaderError on parse failure)
├── validator.py                      (rules engine; returns ValidationResult; CLI entrypoint)
├── errors.py                         (ValidationError, error codes enum)
└── capability_matrix.py              (per-`type` required capability sets)

04_testing/pytest/unit/registry/
├── __init__.py
├── conftest.py                       (shared fixtures)
├── test_loader.py
├── test_validator_schema.py          (top-level field requirements)
├── test_validator_capabilities.py    (per-type capability matrix)
├── test_validator_urls.py            (URL shape rules)
├── test_validator_license.py         (SPDX field rules)
├── test_validator_tested_versions.py
├── test_validator_live_registry.py   (integration: validates the actual live YAML)
└── fixtures/
    ├── valid_minimal.yaml
    ├── valid_full.yaml
    ├── missing_license.yaml
    ├── bad_url_shape.yaml
    ├── slicer_missing_dock_token.yaml
    ├── empty_capabilities.yaml
    └── unknown_type.yaml

scripts/
├── validate-registry.sh              (POSIX wrapper)
└── validate-registry.ps1             (PowerShell wrapper)

hermes3d_gui_contract_kit_v4.1/
├── config/
│   └── external_repos_registry.yaml  (UPDATED: + license, + tested_versions, + dock tokens for slicers/Printrun)
└── scripts/
    └── registry_validator_pseudocode.py  (REPLACED: 1-line stub redirecting to src validator)

.github/workflows/
└── ci.yml                            (UPDATED: Layer A or new sub-step runs the new validator)

.gitignore                            (UPDATED: *.pem, *.key, id_rsa*, *.p12, *.pfx)

hermes3d_gui_contract_kit_v4.1/scripts/install_plan.md  (UPDATED: OrcaSlicer URL fix)

00_overview/
└── PHASE1_COMPLETION_REPORT.md       (NEW: per-task closeout, links to bundle)
```

---

## Tasks

### Task 1: Package skeleton + types

**Files:**
- Create: `03_implementation/src/hermes3d/registry/__init__.py`
- Create: `03_implementation/src/hermes3d/registry/types.py`
- Create: `04_testing/pytest/unit/registry/__init__.py`
- Create: `04_testing/pytest/unit/registry/test_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# 04_testing/pytest/unit/registry/test_loader.py
from hermes3d.registry.types import ToolEntry, AdapterSpec, VersionPolicy

def test_tool_entry_minimal_construction():
    entry = ToolEntry(
        key="example",
        name="Example",
        type="external_app",
        required=True,
        os_support=("windows",),
        version_policy=VersionPolicy(channel="stable", manual_select=True),
        install={"method": "binary"},
        verify={"commands": ["example --version"], "expected": "version"},
        adapter=AdapterSpec(mode="external_process", capabilities=("detect", "launch_external")),
        repo="https://github.com/example/example",
        license="MIT",
        tested_versions=("1.0.0",),
    )
    assert entry.key == "example"
    assert entry.adapter.mode == "external_process"
    assert "detect" in entry.adapter.capabilities
```

- [ ] **Step 2: Run to verify it fails**

```
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python -m pytest 04_testing/pytest/unit/registry/test_loader.py::test_tool_entry_minimal_construction -v
# Expected: ImportError "No module named 'hermes3d.registry'"
```

- [ ] **Step 3: Write `__init__.py` + `types.py`**

```python
# 03_implementation/src/hermes3d/registry/__init__.py
"""Hermes3D external tool registry — typed loader + validator."""
__all__ = ["loader", "validator", "types", "errors", "capability_matrix"]
```

```python
# 03_implementation/src/hermes3d/registry/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Sequence

@dataclass(frozen=True)
class VersionPolicy:
    pin: str | None = None
    channel: str | None = None
    manual_select: bool = False
    locked: str | None = None

    def has_resolution(self) -> bool:
        return any(v for v in (self.pin, self.channel, self.locked)) or self.manual_select

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

- [ ] **Step 4: Run to verify it passes**

```
python -m pytest 04_testing/pytest/unit/registry/test_loader.py::test_tool_entry_minimal_construction -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/ 04_testing/pytest/unit/registry/__init__.py 04_testing/pytest/unit/registry/test_loader.py
git commit -m "feat(registry): typed dataclasses for tool entries + version policy + adapter spec"
```

### Task 2: Errors module + base ValidationError

**Files:**
- Create: `03_implementation/src/hermes3d/registry/errors.py`
- Modify: `04_testing/pytest/unit/registry/test_loader.py` (add error tests)

- [ ] **Step 1: Write the failing tests**

```python
# Append to test_loader.py
from hermes3d.registry.errors import ValidationError, ErrorCode

def test_error_code_enum_has_expected_values():
    assert ErrorCode.MISSING_REQUIRED_FIELD.value == "MISSING_REQUIRED_FIELD"
    assert ErrorCode.INVALID_URL_SHAPE.value == "INVALID_URL_SHAPE"
    assert ErrorCode.MISSING_LICENSE.value == "MISSING_LICENSE"
    assert ErrorCode.MISSING_DOCK_CAPABILITY.value == "MISSING_DOCK_CAPABILITY"
    assert ErrorCode.INVALID_LICENSE.value == "INVALID_LICENSE"
    assert ErrorCode.UNKNOWN_TYPE.value == "UNKNOWN_TYPE"

def test_validation_error_serializes():
    err = ValidationError(
        tool_id="example",
        code=ErrorCode.MISSING_LICENSE,
        message="missing required field 'license'",
        severity="error",
    )
    d = err.to_dict()
    assert d["tool_id"] == "example"
    assert d["code"] == "MISSING_LICENSE"
    assert d["severity"] == "error"
```

- [ ] **Step 2: Run to verify failure** (`ImportError` expected)

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

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/errors.py 04_testing/pytest/unit/registry/test_loader.py
git commit -m "feat(registry): structured error model with ErrorCode enum"
```

### Task 3: Capability matrix module

**Files:**
- Create: `03_implementation/src/hermes3d/registry/capability_matrix.py`
- Create: `04_testing/pytest/unit/registry/test_validator_capabilities.py`

- [ ] **Step 1: Write the failing tests**

```python
# 04_testing/pytest/unit/registry/test_validator_capabilities.py
import pytest
from hermes3d.registry.capability_matrix import (
    required_capabilities_for_type,
    KNOWN_TYPES,
)

def test_slicer_requires_external_launch_and_dock():
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
    assert required_capabilities_for_type("nonexistent_type") == frozenset()

def test_known_types_includes_all_locked_categories():
    expected = {
        "external_app", "mcp_provider", "slicer", "printer_control_usb",
        "printer_api", "external_web_ui", "printer_api_and_web_ui",
    }
    assert expected.issubset(KNOWN_TYPES)
```

- [ ] **Step 2: Run to verify failure** (`ImportError`)

- [ ] **Step 3: Implement `capability_matrix.py`**

```python
# 03_implementation/src/hermes3d/registry/capability_matrix.py
"""Per-`type` required adapter capabilities.

Derived from:
- `01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md` §6 work-items list
- `03_implementation/adapter_registry/README.md` §1 taxonomy + §5 capability flags
- User's locked requirement: every UI-bearing tool supportable in BOTH docked AND external modes
"""
from __future__ import annotations

# Per-type required capability sets. A `dock_*` token satisfies the
# "must dock" requirement; the validator accepts any token starting with
# "dock_" (dock_if_supported, dock_if_allowed) for flexibility.
_REQUIRED: dict[str, frozenset[str]] = {
    "external_app":            frozenset({"launch_external", "dock_if_supported"}),
    "mcp_provider":            frozenset(),  # provider, no UI surface
    "slicer":                  frozenset({"launch_external", "dock_if_allowed"}),
    "printer_control_usb":     frozenset({"launch_external", "dock_if_allowed"}),
    "printer_api":             frozenset(),  # headless API, no UI
    "external_web_ui":         frozenset({"dock_if_allowed", "fullscreen_external"}),
    "printer_api_and_web_ui":  frozenset({"dock_if_allowed"}),
}

KNOWN_TYPES: frozenset[str] = frozenset(_REQUIRED.keys())

def required_capabilities_for_type(tool_type: str) -> frozenset[str]:
    """Return required capability tokens for a given tool type, or empty for unknown types."""
    return _REQUIRED.get(tool_type, frozenset())

def is_known_type(tool_type: str) -> bool:
    return tool_type in KNOWN_TYPES
```

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/capability_matrix.py 04_testing/pytest/unit/registry/test_validator_capabilities.py
git commit -m "feat(registry): per-type required capability matrix"
```

### Task 4: Loader

**Files:**
- Create: `03_implementation/src/hermes3d/registry/loader.py`
- Create: `04_testing/pytest/unit/registry/conftest.py`
- Create: `04_testing/pytest/unit/registry/fixtures/valid_minimal.yaml`
- Modify: `04_testing/pytest/unit/registry/test_loader.py` (add loader tests)

- [ ] **Step 1: Write the fixture**

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

- [ ] **Step 2: Write conftest**

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

- [ ] **Step 3: Write the failing loader tests**

```python
# Append to test_loader.py
from hermes3d.registry.loader import load_registry, LoaderError

def test_load_minimal_returns_one_tool(fixture_path):
    entries = load_registry(fixture_path("valid_minimal.yaml"))
    assert len(entries) == 1
    entry = entries[0]
    assert entry.key == "example"
    assert entry.name == "Example"
    assert entry.type == "external_app"
    assert entry.required is True
    assert entry.adapter.mode == "external_process"
    assert "launch_external" in entry.adapter.capabilities
    assert entry.license == "MIT"
    assert entry.tested_versions == ("1.0.0", "1.1.0")

def test_load_missing_file_raises(tmp_path):
    with pytest.raises(LoaderError, match="not found"):
        load_registry(tmp_path / "nonexistent.yaml")
```

- [ ] **Step 4: Run to verify failure**

- [ ] **Step 5: Implement `loader.py`**

```python
# 03_implementation/src/hermes3d/registry/loader.py
"""Parse external_repos_registry.yaml into typed ToolEntry objects."""
from __future__ import annotations
from pathlib import Path
from typing import Sequence
import yaml

from .types import AdapterSpec, ToolEntry, VersionPolicy

class LoaderError(Exception):
    """Raised on file-not-found or top-level YAML structure errors."""

def _coerce_version_policy(d: dict) -> VersionPolicy:
    return VersionPolicy(
        pin=d.get("pin"),
        channel=d.get("channel"),
        manual_select=bool(d.get("manual_select", False)),
        locked=d.get("locked"),
    )

def _coerce_adapter(d: dict) -> AdapterSpec:
    caps = d.get("capabilities") or ()
    if not isinstance(caps, (list, tuple)):
        caps = ()
    return AdapterSpec(mode=str(d.get("mode", "")), capabilities=tuple(str(c) for c in caps))

def _coerce_entry(key: str, raw: dict) -> ToolEntry:
    os_support = raw.get("os_support") or ()
    if not isinstance(os_support, (list, tuple)):
        os_support = ()
    tested = raw.get("tested_versions") or ()
    if not isinstance(tested, (list, tuple)):
        tested = ()
    return ToolEntry(
        key=key,
        name=str(raw.get("name", "")),
        type=str(raw.get("type", "")),
        required=bool(raw.get("required", False)),
        os_support=tuple(str(o) for o in os_support),
        version_policy=_coerce_version_policy(raw.get("version_policy") or {}),
        install=raw.get("install") or {},
        verify=raw.get("verify") or {},
        adapter=_coerce_adapter(raw.get("adapter") or {}),
        license=str(raw.get("license", "")),
        tested_versions=tuple(str(v) for v in tested),
        repo=raw.get("repo"),
        source=raw.get("source"),
        homepage=raw.get("homepage"),
    )

def load_registry(path: Path) -> list[ToolEntry]:
    """Load and parse a registry YAML; returns ordered list of entries."""
    if not path.exists():
        raise LoaderError(f"registry not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tools = data.get("tools") if isinstance(data, dict) and "tools" in data else data
    if not isinstance(tools, dict) or not tools:
        raise LoaderError("registry must contain non-empty 'tools' object")
    return [_coerce_entry(str(k), v) for k, v in tools.items() if isinstance(v, dict)]
```

- [ ] **Step 6: Run to verify it passes**

- [ ] **Step 7: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/loader.py 04_testing/pytest/unit/registry/conftest.py 04_testing/pytest/unit/registry/fixtures/ 04_testing/pytest/unit/registry/test_loader.py
git commit -m "feat(registry): YAML loader returns typed ToolEntry list"
```

### Task 5: Validator — schema rules

**Files:**
- Create: `03_implementation/src/hermes3d/registry/validator.py`
- Create: `04_testing/pytest/unit/registry/test_validator_schema.py`
- Create: `04_testing/pytest/unit/registry/fixtures/missing_license.yaml`
- Create: `04_testing/pytest/unit/registry/fixtures/empty_capabilities.yaml`

- [ ] **Step 1: Write fixtures**

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
    # license deliberately omitted
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

- [ ] **Step 2: Write the failing tests**

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

def test_missing_license_fails_with_correct_code(fixture_path):
    entries = load_registry(fixture_path("missing_license.yaml"))
    result = validate(entries)
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert ErrorCode.MISSING_LICENSE in codes

def test_empty_capabilities_fails(fixture_path):
    entries = load_registry(fixture_path("empty_capabilities.yaml"))
    result = validate(entries)
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert ErrorCode.EMPTY_CAPABILITIES in codes
```

- [ ] **Step 3: Run to verify failure**

- [ ] **Step 4: Implement `validator.py`** (skeleton — capability + URL rules added in Tasks 6-7)

```python
# 03_implementation/src/hermes3d/registry/validator.py
"""Hermes3D registry validator — production implementation.

CLI: python -m hermes3d.registry.validator [PATH]

Returns exit 0 on PASS, 1 on FAIL. Output is structured (text + optional --json).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import argparse
import json
import sys
from typing import Sequence

from .capability_matrix import is_known_type, required_capabilities_for_type
from .errors import ErrorCode, ValidationError
from .loader import LoaderError, load_registry
from .types import ToolEntry

# License must be a non-empty SPDX-like string; we don't currently maintain
# a closed enum (there are >100 valid SPDX ids and the registry will use a
# small subset). Empty / "Unknown" / placeholder values fail.
_INVALID_LICENSE_VALUES = frozenset({"", "unknown", "tbd", "todo", "n/a", "none"})

@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    checked: int
    errors: tuple[ValidationError, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "errors": [e.to_dict() for e in self.errors],
        }

def _check_license(entry: ToolEntry) -> list[ValidationError]:
    if not entry.license:
        return [ValidationError(entry.key, ErrorCode.MISSING_LICENSE, "missing required field 'license'")]
    if entry.license.strip().lower() in _INVALID_LICENSE_VALUES:
        return [ValidationError(entry.key, ErrorCode.INVALID_LICENSE,
                                f"license value '{entry.license}' is not a real SPDX id")]
    return []

def _check_capabilities(entry: ToolEntry) -> list[ValidationError]:
    errs: list[ValidationError] = []
    if not entry.adapter.capabilities:
        errs.append(ValidationError(entry.key, ErrorCode.EMPTY_CAPABILITIES,
                                    "adapter.capabilities must be non-empty"))
    if not is_known_type(entry.type):
        errs.append(ValidationError(entry.key, ErrorCode.UNKNOWN_TYPE,
                                    f"unknown type '{entry.type}'", severity="warning"))
    return errs

def _check_entry(entry: ToolEntry) -> list[ValidationError]:
    errs: list[ValidationError] = []
    errs.extend(_check_license(entry))
    errs.extend(_check_capabilities(entry))
    # URL shape + per-type capability matrix added in Tasks 6 + 7
    return errs

def validate(entries: Sequence[ToolEntry]) -> ValidationResult:
    all_errors: list[ValidationError] = []
    for entry in entries:
        all_errors.extend(_check_entry(entry))
    blocking = [e for e in all_errors if e.severity == "error"]
    return ValidationResult(ok=not blocking, checked=len(entries), errors=tuple(all_errors))

def _default_registry_path() -> Path:
    """Anchor the default to repo root, not CWD — fixes Phase 0 finding LOW-8."""
    return Path(__file__).resolve().parents[4] / "hermes3d_gui_contract_kit_v4.1" / "config" / "external_repos_registry.yaml"

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes3d.registry.validator")
    parser.add_argument("path", nargs="?", type=Path, default=_default_registry_path())
    parser.add_argument("--json", action="store_true", help="emit JSON instead of human text")
    args = parser.parse_args(argv)
    try:
        entries = load_registry(args.path)
    except LoaderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    result = validate(entries)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.ok:
            print(f"Registry validation PASS: {result.checked} tools checked")
        else:
            print(f"Registry validation FAILED: {result.checked} tools checked, {len(result.errors)} issues")
            for err in result.errors:
                print(f"- [{err.severity}] {err.tool_id} {err.code.value}: {err.message}")
    return 0 if result.ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run schema tests to verify they pass**

- [ ] **Step 6: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/validator.py 04_testing/pytest/unit/registry/test_validator_schema.py 04_testing/pytest/unit/registry/fixtures/missing_license.yaml 04_testing/pytest/unit/registry/fixtures/empty_capabilities.yaml
git commit -m "feat(registry): validator with license + structural rules + CLI"
```

### Task 6: Validator — URL shape rules

**Files:**
- Modify: `03_implementation/src/hermes3d/registry/validator.py` (add `_check_url`)
- Create: `04_testing/pytest/unit/registry/fixtures/bad_url_shape.yaml`
- Create: `04_testing/pytest/unit/registry/test_validator_urls.py`

- [ ] **Step 1: Write the fixture**

```yaml
# fixtures/bad_url_shape.yaml
tools:
  bad_one:
    name: Bad
    type: external_app
    repo: ""                              # empty -> fail
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
    repo: "https//github.com/x/y"        # missing colon -> fail
    required: false
    os_support: [windows]
    version_policy: {channel: stable, manual_select: true}
    install: {method: binary}
    verify: {commands: ["x --version"], expected: "v"}
    adapter: {mode: external_process, capabilities: [launch_external, dock_if_supported]}
    license: MIT
    tested_versions: ["1.0.0"]
```

- [ ] **Step 2: Write the failing tests**

```python
# 04_testing/pytest/unit/registry/test_validator_urls.py
from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import validate
from hermes3d.registry.errors import ErrorCode

def test_bad_url_shape_flagged(fixture_path):
    entries = load_registry(fixture_path("bad_url_shape.yaml"))
    result = validate(entries)
    assert not result.ok
    codes = {(e.tool_id, e.code) for e in result.errors}
    assert ("bad_one", ErrorCode.INVALID_URL_SHAPE) in codes
    assert ("bad_two", ErrorCode.INVALID_URL_SHAPE) in codes
```

- [ ] **Step 3: Add `_check_url` to `validator.py`**

```python
# Insert into validator.py, near the other _check_* helpers
import re
_URL_SHAPE = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")

def _check_url(entry: ToolEntry) -> list[ValidationError]:
    url = entry.reference_url()
    if url is None:
        return [ValidationError(entry.key, ErrorCode.MISSING_REQUIRED_FIELD,
                                "must include repo, source, or homepage")]
    if not isinstance(url, str) or not url.strip() or not _URL_SHAPE.match(url):
        return [ValidationError(entry.key, ErrorCode.INVALID_URL_SHAPE,
                                f"reference URL '{url}' is not a well-formed http(s) URL")]
    return []

# And extend _check_entry to call it:
def _check_entry(entry: ToolEntry) -> list[ValidationError]:
    errs: list[ValidationError] = []
    errs.extend(_check_license(entry))
    errs.extend(_check_capabilities(entry))
    errs.extend(_check_url(entry))
    return errs
```

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/validator.py 04_testing/pytest/unit/registry/test_validator_urls.py 04_testing/pytest/unit/registry/fixtures/bad_url_shape.yaml
git commit -m "feat(registry): URL shape validation"
```

### Task 7: Validator — per-type capability matrix

**Files:**
- Modify: `03_implementation/src/hermes3d/registry/validator.py` (add `_check_per_type_capabilities`)
- Create: `04_testing/pytest/unit/registry/fixtures/slicer_missing_dock_token.yaml`

- [ ] **Step 1: Write the fixture**

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
    # NB: no dock_* token despite type=slicer
```

- [ ] **Step 2: Write the failing test**

```python
# Append to test_validator_capabilities.py
from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import validate
from hermes3d.registry.errors import ErrorCode

def test_slicer_missing_dock_token_flagged(fixture_path):
    entries = load_registry(fixture_path("slicer_missing_dock_token.yaml"))
    result = validate(entries)
    assert not result.ok
    codes = {(e.tool_id, e.code) for e in result.errors}
    assert ("bad_slicer", ErrorCode.MISSING_DOCK_CAPABILITY) in codes
```

- [ ] **Step 3: Implement per-type check**

```python
# Add to validator.py:
def _check_per_type_capabilities(entry: ToolEntry) -> list[ValidationError]:
    required = required_capabilities_for_type(entry.type)
    if not required:
        return []
    caps = set(entry.adapter.capabilities)
    errs: list[ValidationError] = []
    for req in required:
        if req.startswith("dock_"):
            # any dock_* token satisfies the dock requirement
            if not any(c.startswith("dock_") for c in caps):
                errs.append(ValidationError(
                    entry.key, ErrorCode.MISSING_DOCK_CAPABILITY,
                    f"type '{entry.type}' requires a dock capability (e.g. {req}); none declared",
                ))
        elif req == "launch_external":
            if "launch_external" not in caps and "fullscreen_external" not in caps:
                errs.append(ValidationError(
                    entry.key, ErrorCode.MISSING_EXTERNAL_LAUNCH_CAPABILITY,
                    f"type '{entry.type}' requires 'launch_external' or equivalent; none declared",
                ))
        elif req not in caps:
            # Other generic required tokens (e.g. fullscreen_external)
            errs.append(ValidationError(
                entry.key, ErrorCode.MISSING_REQUIRED_FIELD,
                f"type '{entry.type}' requires capability '{req}'",
            ))
    return errs

# Extend _check_entry:
def _check_entry(entry: ToolEntry) -> list[ValidationError]:
    errs: list[ValidationError] = []
    errs.extend(_check_license(entry))
    errs.extend(_check_capabilities(entry))
    errs.extend(_check_url(entry))
    errs.extend(_check_per_type_capabilities(entry))
    return errs
```

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/validator.py 04_testing/pytest/unit/registry/test_validator_capabilities.py 04_testing/pytest/unit/registry/fixtures/slicer_missing_dock_token.yaml
git commit -m "feat(registry): per-type capability matrix validation"
```

### Task 8: Validator — tested_versions rule

**Files:**
- Modify: `03_implementation/src/hermes3d/registry/validator.py`
- Create: `04_testing/pytest/unit/registry/test_validator_tested_versions.py`

- [ ] **Step 1: Write the failing test**

```python
# 04_testing/pytest/unit/registry/test_validator_tested_versions.py
from hermes3d.registry.types import AdapterSpec, ToolEntry, VersionPolicy
from hermes3d.registry.validator import validate
from hermes3d.registry.errors import ErrorCode

def _entry_factory(**overrides):
    base = dict(
        key="x",
        name="X",
        type="external_app",
        required=True,
        os_support=("windows",),
        version_policy=VersionPolicy(channel="stable", manual_select=True),
        install={"method": "binary"},
        verify={"commands": ["x --version"], "expected": "v"},
        adapter=AdapterSpec(mode="external_process", capabilities=("launch_external", "dock_if_supported")),
        license="MIT",
        tested_versions=("1.0.0",),
        repo="https://github.com/x/y",
    )
    base.update(overrides)
    return ToolEntry(**base)

def test_empty_tested_versions_flagged():
    entry = _entry_factory(tested_versions=())
    result = validate([entry])
    codes = {e.code for e in result.errors}
    assert ErrorCode.EMPTY_TESTED_VERSIONS in codes

def test_with_tested_versions_passes():
    entry = _entry_factory(tested_versions=("1.0.0", "2.0.0"))
    result = validate([entry])
    assert result.ok, [e.to_dict() for e in result.errors]
```

- [ ] **Step 2: Run to verify failure**

- [ ] **Step 3: Add `_check_tested_versions` to `validator.py`**

```python
def _check_tested_versions(entry: ToolEntry) -> list[ValidationError]:
    if not entry.tested_versions:
        return [ValidationError(
            entry.key, ErrorCode.EMPTY_TESTED_VERSIONS,
            "tested_versions must be a non-empty list (record at least one version that was verified)",
            severity="error",
        )]
    return []

# Extend _check_entry:
def _check_entry(entry: ToolEntry) -> list[ValidationError]:
    errs: list[ValidationError] = []
    errs.extend(_check_license(entry))
    errs.extend(_check_capabilities(entry))
    errs.extend(_check_url(entry))
    errs.extend(_check_per_type_capabilities(entry))
    errs.extend(_check_tested_versions(entry))
    return errs
```

- [ ] **Step 4: Run to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add 03_implementation/src/hermes3d/registry/validator.py 04_testing/pytest/unit/registry/test_validator_tested_versions.py
git commit -m "feat(registry): tested_versions required field"
```

### Task 9: Update live registry YAML to satisfy new rules

**Files:**
- Modify: `hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml`

- [ ] **Step 1: Plan the YAML edits**

For each of the 12 entries, add:
- `license:` (SPDX id — see table below)
- `tested_versions:` (one or two known-good versions per Phase 0 hardware-fleet experience; use placeholders like `["TBD-pending-fleet-validation"]` only if no version has been verified — but per validator the placeholder must NOT be in `_INVALID_LICENSE_VALUES`; use a real version string when known)

For slicers (`prusa_slicer`, `orca_slicer`, `flsun_slicer`, `cura`) and `printrun`: add `dock_if_allowed` to `adapter.capabilities`.

For `octoprint`: add `fullscreen_external` to `adapter.capabilities` for vocabulary consistency with the other web UIs.

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

Tested versions: use latest stable as of 2026-04-30 (verify against vendor sites — keep conservative, do not invent). If unsure, use `["TBD-2026-04-30"]` with a comment, but mark as a Phase 1 follow-up to verify.

- [ ] **Step 2: Apply the edits**

Edit each entry adding the three fields. Example for `blender`:

```yaml
  blender:
    name: Blender
    type: external_app
    repo: https://github.com/blender/blender
    homepage: https://www.blender.org/download/
    required: true
    os_support: [windows, linux]
    version_policy: {channel: stable, manual_select: true}
    install: {method: binary_or_existing_install, windows_hint: "Detect blender.exe", linux_hint: "Detect blender in PATH"}
    verify: {commands: ["blender --version"], expected: "version output contains Blender"}
    adapter: {mode: external_process, capabilities: [detect, launch_external, dock_if_supported, screenshot_source]}
    license: GPL-3.0-or-later
    tested_versions: ["4.2.0"]
```

(Use the appropriate license + version for each entry.)

- [ ] **Step 3: Run validator against the live YAML**

```
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python -m hermes3d.registry.validator hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml
```
Expected: `Registry validation PASS: 12 tools checked`

- [ ] **Step 4: Run integration test that validates the live YAML**

```python
# 04_testing/pytest/unit/registry/test_validator_live_registry.py
from pathlib import Path
import pytest
from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import validate

REPO_ROOT = Path(__file__).resolve().parents[4]
LIVE_REGISTRY = REPO_ROOT / "hermes3d_gui_contract_kit_v4.1" / "config" / "external_repos_registry.yaml"

@pytest.mark.skipif(not LIVE_REGISTRY.exists(), reason="kit registry not present in checkout")
def test_live_registry_passes_hardened_validator():
    entries = load_registry(LIVE_REGISTRY)
    result = validate(entries)
    assert result.ok, "live registry FAILED hardened validation:\n" + "\n".join(
        f"- {e.tool_id} [{e.severity}] {e.code.value}: {e.message}" for e in result.errors
    )
    assert result.checked == 12  # 10 locked + Cura + experimental MCP provider
```

- [ ] **Step 5: Commit**

```bash
git add hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml 04_testing/pytest/unit/registry/test_validator_live_registry.py
git commit -m "feat(registry): populate license + tested_versions + dock tokens for all 12 entries"
```

### Task 10: Replace stale pseudocode + thin CLI wrappers

**Files:**
- Modify: `hermes3d_gui_contract_kit_v4.1/scripts/registry_validator_pseudocode.py` (replace contents)
- Create: `scripts/validate-registry.sh`
- Create: `scripts/validate-registry.ps1`

- [ ] **Step 1: Replace pseudocode with redirect stub**

```python
# hermes3d_gui_contract_kit_v4.1/scripts/registry_validator_pseudocode.py
"""DEPRECATED — see the production validator under src/hermes3d/registry/.

This file used to contain a pseudocode validator that referenced an obsolete
schema (`repositories` / `display_name` / `repo_url`) which never matched the
real registry (`tools` / `name` / `repo`). It was misleading reference
material. The real implementation now lives at:

    03_implementation/src/hermes3d/registry/validator.py

Run:

    python -m hermes3d.registry.validator [PATH-TO-REGISTRY-YAML]

or use the wrapper scripts:

    bash scripts/validate-registry.sh
    powershell scripts/validate-registry.ps1

The kit also still ships a minimal baseline validator at
`hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py` for use by
implementers who only have the kit checked out.
"""
raise SystemExit(
    "registry_validator_pseudocode.py is deprecated. "
    "Use: python -m hermes3d.registry.validator <path>"
)
```

- [ ] **Step 2: Write the wrapper scripts**

```bash
# scripts/validate-registry.sh
#!/usr/bin/env bash
# Hermes3D — wrapper for the production registry validator.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  "$PY" -m hermes3d.registry.validator "$@"
```

```powershell
# scripts/validate-registry.ps1
# Hermes3D — wrapper for the production registry validator.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    python -m hermes3d.registry.validator @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
```

- [ ] **Step 3: Make the bash script executable + test both wrappers**

```bash
chmod +x scripts/validate-registry.sh
bash scripts/validate-registry.sh   # expect: Registry validation PASS: 12 tools checked
```

- [ ] **Step 4: Verify the deprecated stub fails clearly**

```bash
python hermes3d_gui_contract_kit_v4.1/scripts/registry_validator_pseudocode.py 2>&1
# expect: SystemExit with deprecation message; exit code != 0
```

- [ ] **Step 5: Commit**

```bash
git add hermes3d_gui_contract_kit_v4.1/scripts/registry_validator_pseudocode.py scripts/validate-registry.sh scripts/validate-registry.ps1
git commit -m "chore(registry): replace stale pseudocode + add CLI wrappers"
```

### Task 11: CI gate

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add a step to Layer A** (simplest place; Layer A already does ruff + forbidden-pattern scan)

Insert into the Layer A job, after the existing forbidden-pattern step:

```yaml
      - name: Layer A — registry validator
        run: |
          PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
            python -m hermes3d.registry.validator \
              hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml
```

(If the editable install isn't already done in Layer A, add `pip install -e 03_implementation/[all]` before the validator step. Inspect the existing Layer A YAML to confirm.)

- [ ] **Step 2: Push to a remote test branch** (NOT this PR's branch — quick validation only)

Skip this step if the workflow change is small and unambiguous; trust CI on the eventual PR push.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci(registry): gate the hardened validator in Layer A"
```

### Task 12: .gitignore defensive addendum + Orca URL fix

**Files:**
- Modify: `.gitignore`
- Modify: `hermes3d_gui_contract_kit_v4.1/scripts/install_plan.md`

- [ ] **Step 1: Add the defensive patterns**

```
## Sensitive material — defensive (no current matches; keep this way)
*.pem
*.key
id_rsa*
*.p12
*.pfx
```

Append to `.gitignore` after the "Environment / secrets" section.

- [ ] **Step 2: Fix the Orca URL**

In `install_plan.md` line 21, change `https://github.com/OrcaSlicer/OrcaSlicer` → `https://github.com/SoftFever/OrcaSlicer` (matches the canonical upstream the registry uses).

- [ ] **Step 3: Commit**

```bash
git add .gitignore hermes3d_gui_contract_kit_v4.1/scripts/install_plan.md
git commit -m "chore: defensive secret-vector .gitignore + fix install_plan OrcaSlicer URL"
```

### Task 13: Phase 1 completion report + signed bundle

**Files:**
- Create: `00_overview/PHASE1_COMPLETION_REPORT.md`

- [ ] **Step 1: Write the report** (modeled on `PHASE0_BASELINE_REPORT.md`)

Sections:
- Branch + commit + delta summary
- Per-task scorecard (12 tasks, all complete + commits)
- New code surface: lines, files, modules
- Validator findings against live registry: PASS, 12 tools
- CI gate added: Layer A registry-validator step
- Constraints honored: 0 source changes outside scope, rc1 untouched, no new deps, no secrets
- Phase 1 closed-out items vs Phase 0 outstanding-list (per Phase 0 baseline §"Phase 1 readiness — summary")
- What remains for Phase 2/3 (UI shell, env-detect, adapter shell)
- Signed bundle path + sha256

- [ ] **Step 2: Build + verify the Phase 1 signed bundle from clean tree**

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  bash scripts/build-bundle.sh --output 05_truth_proof/bundles/
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python 05_truth_proof/conformance_runner.py --bundle <path>
# expect: OK — signature + file hashes + cross-refs verified, dirty=False
```

- [ ] **Step 3: Commit the report**

```bash
git add 00_overview/PHASE1_COMPLETION_REPORT.md
git commit -m "phase-1: completion report (registry + validators GREEN, 12 tools, CI gated)"
```

### Task 14: Push branch + open PR + STOP

- [ ] **Step 1: Push**

```bash
git push -u origin feat/phase-1-foundation
```

- [ ] **Step 2: Open PR targeting `develop`**

`gh pr create --base develop --head feat/phase-1-foundation --title "Phase 1 — Registry + Validators (typed loader, hardened rules, CI gated)" --body-file <body.md>`

PR body should include:
- Summary
- Per-task scorecard
- Validator output PASS line
- Bundle path + sha256
- Constraints honored
- "Stop after merge — Phase 2 awaits explicit trigger"

- [ ] **Step 3: Confirm CI passes**

`gh pr checks <num> --watch`. If anything fails: STOP, diagnose, fix forward (no downgrades per project standard).

- [ ] **Step 4: STOP — wait for user approval**

Do not auto-merge. Do not start Phase 2 without an explicit user trigger.

---

## Self-Review

**Spec coverage check:**
- ✅ Phase 0 finding "stale pseudocode" → Task 10
- ✅ Phase 0 finding "no `license` field" → Tasks 5 + 9
- ✅ Phase 0 finding "no per-type capability matrix" → Tasks 3 + 7
- ✅ Phase 0 finding "no `tested_versions`" → Task 8 + 9
- ✅ Phase 0 finding "no URL shape check" → Task 6
- ✅ Phase 0 finding "no structured error model" → Task 2
- ✅ Phase 0 finding "default-path CWD-relative" → Task 5 (`_default_registry_path`)
- ✅ Phase 0 finding "Orca URL drift in install_plan" → Task 12
- ✅ Phase 0 finding ".gitignore missing `*.pem` etc" → Task 12
- ✅ Phase 0 finding "validator must enforce dock token per-type" → Tasks 3 + 7
- ✅ Phase 0 finding "structured error model" → Task 2
- ❌ Phase 0 finding "single-required-MCP-provider rule" → DEFERRED (rule is fine to leave for Phase 1.1; only one rule, low risk; not blocking)

**Out-of-scope items (deliberately deferred):**
- env-detect.py + JSON Schema + fixtures → Phase 3 (kit assignment) or earlier follow-up
- Adapter shell (ToolAdapter Protocol + 11 skeletons + JSON config schemas) → Phase 3
- ADR-005 / 006 / 007 / 008 → Phase 3-5 when relevant code lands
- AUDIT_LOG_SCHEMA + RATE_LIMIT_POLICY → Phase 4-5

**Placeholder scan:** None found. Every step has actual code or a concrete command.

**Type consistency:** `ToolEntry`, `AdapterSpec`, `VersionPolicy`, `ValidationError`, `ValidationResult`, `ErrorCode` are used identically across Tasks 1-9. `ErrorCode.MISSING_LICENSE`, `ErrorCode.INVALID_URL_SHAPE`, etc. all consistent.

**Frequent commits:** 13 commits across 14 tasks. Each commit is reviewable, runnable, and self-contained.

**TDD pattern:** Every task that ships code has "write test → confirm fail → implement → confirm pass → commit" structure.

**DRY:** Loader + validator + types separated by responsibility. No duplication of capability matrix logic — it lives in `capability_matrix.py` only.

**YAGNI:** No abstractions for hypothetical future tools. No "extensibility hooks". The validator does exactly what Phase 0 audit requested, nothing more.

---

## Execution

Choose execution mode after reviewing this plan:

1. **Subagent-Driven Development** (recommended for Phase 1 size): dispatch a fresh subagent per task or task-group, review between tasks. Avoids the agent-stall pattern by keeping each subagent's scope tight (~10-30 min of work).
2. **Inline Execution** (alternative): execute tasks sequentially in the coordinator session with checkpoints every 3-4 tasks.

Both modes should commit after each task per the plan and never batch tasks across multiple commits.
