"""Material temperature window gate.

Status: runnable
Gate ID: ``safety.material_temperature_window``

Loads :data:`MATERIAL_DB_DEFAULT_PATH` (a YAML file shipped beside this
module) and rejects any submitted print profile whose ``nozzle_temp``
or ``bed_temp`` falls outside the named material's safe window.

The database is user-extensible: if a sibling
``material_db.user.yaml`` exists, its entries override / augment the
defaults. Material lookup is case-insensitive but prefers the canonical
casing (PLA, PETG, ABS, TPU, PC, Nylon).

Override escape hatch:
    Set ``HERMES3D_OVERRIDE_MATERIAL_WINDOW=1`` in the environment to
    *log* a violation but allow the print. Used for paid-thermistor
    experimental materials and developer test prints. Logged at WARNING
    so the override is loud and auditable.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)


# YAML is allowed (PyYAML is not a *new* dep — pyproject already pulls
# it transitively via FastAPI/Pydantic). We import lazily so the module
# stays importable in environments where PyYAML is absent.

MATERIAL_DB_DEFAULT_PATH = Path(__file__).with_name("material_db.yaml")
MATERIAL_DB_USER_PATH = Path(__file__).with_name("material_db.user.yaml")
OVERRIDE_ENV_VAR = "HERMES3D_OVERRIDE_MATERIAL_WINDOW"


@dataclass(frozen=True)
class MaterialWindow:
    """Safe temperature window for one material family."""

    name: str
    nozzle_min_c: float
    nozzle_max_c: float
    bed_min_c: float
    bed_max_c: float
    notes: str = ""

    def contains(self, *, nozzle_c: float, bed_c: float) -> bool:
        return (
            self.nozzle_min_c <= nozzle_c <= self.nozzle_max_c
            and self.bed_min_c <= bed_c <= self.bed_max_c
        )


@dataclass
class MaterialDB:
    """In-memory material database. Constructed via :func:`load_material_db`."""

    materials: dict[str, MaterialWindow] = field(default_factory=dict)

    def get(self, name: str) -> MaterialWindow | None:
        # Case-insensitive lookup with canonical fallback.
        if name in self.materials:
            return self.materials[name]
        for canon, mw in self.materials.items():
            if canon.lower() == name.lower():
                return mw
        return None

    def names(self) -> list[str]:
        return sorted(self.materials.keys())


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            f"material_window: PyYAML required to load {path} (install pyyaml)"
        ) from exc
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping at top level, got {type(data)}")
    return data


def load_material_db(
    *,
    default_path: Path | None = None,
    user_path: Path | None = None,
) -> MaterialDB:
    """Load the material database, applying user overrides on top.

    Both paths are optional. Missing files are treated as empty. The
    default path is :data:`MATERIAL_DB_DEFAULT_PATH`; the user path is
    :data:`MATERIAL_DB_USER_PATH`.
    """
    default_path = default_path or MATERIAL_DB_DEFAULT_PATH
    user_path = user_path or MATERIAL_DB_USER_PATH

    raw_default = _load_yaml(default_path).get("materials", {}) or {}
    raw_user = _load_yaml(user_path).get("materials", {}) or {}

    merged: dict[str, dict[str, Any]] = {}
    for name, entry in raw_default.items():
        if isinstance(entry, dict):
            merged[name] = dict(entry)
    for name, entry in raw_user.items():
        if isinstance(entry, dict):
            merged.setdefault(name, {}).update(entry)

    materials: dict[str, MaterialWindow] = {}
    for name, entry in merged.items():
        try:
            materials[name] = MaterialWindow(
                name=name,
                nozzle_min_c=float(entry["nozzle_min_c"]),
                nozzle_max_c=float(entry["nozzle_max_c"]),
                bed_min_c=float(entry["bed_min_c"]),
                bed_max_c=float(entry["bed_max_c"]),
                notes=str(entry.get("notes", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"material_window: malformed entry for {name!r}: {exc}"
            ) from exc
    return MaterialDB(materials=materials)


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MaterialCheckResult:
    passed: bool
    material: str
    nozzle_c: float
    bed_c: float
    window: MaterialWindow | None
    reason: str
    overridden: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "material": self.material,
            "nozzle_c": self.nozzle_c,
            "bed_c": self.bed_c,
            "window": (
                {
                    "name": self.window.name,
                    "nozzle_min_c": self.window.nozzle_min_c,
                    "nozzle_max_c": self.window.nozzle_max_c,
                    "bed_min_c": self.window.bed_min_c,
                    "bed_max_c": self.window.bed_max_c,
                }
                if self.window is not None
                else None
            ),
            "reason": self.reason,
            "overridden": self.overridden,
        }


def _override_active(env: dict[str, str] | None = None) -> bool:
    src = env if env is not None else os.environ
    val = src.get(OVERRIDE_ENV_VAR, "0").strip().lower()
    return val in ("1", "true", "yes", "on")


def check_material_window(
    *,
    material: str,
    nozzle_c: float,
    bed_c: float,
    db: MaterialDB | None = None,
    env: dict[str, str] | None = None,
) -> MaterialCheckResult:
    """Validate a profile's temperatures against the material's window.

    Returns a :class:`MaterialCheckResult`. ``passed`` is True iff
    temperatures are inside the window OR the
    :data:`OVERRIDE_ENV_VAR` environment escape hatch is active. When
    overridden, ``overridden=True`` and a WARNING is logged.
    """
    db = db or load_material_db()
    window = db.get(material)

    if window is None:
        if _override_active(env):
            LOG.warning(
                "material_window: unknown material %r — OVERRIDE active, allowing",
                material,
            )
            return MaterialCheckResult(
                passed=True,
                material=material,
                nozzle_c=nozzle_c,
                bed_c=bed_c,
                window=None,
                reason=f"Unknown material {material!r}; override active",
                overridden=True,
            )
        return MaterialCheckResult(
            passed=False,
            material=material,
            nozzle_c=nozzle_c,
            bed_c=bed_c,
            window=None,
            reason=(
                f"Unknown material {material!r}; "
                f"known: {', '.join(db.names()) or '(empty db)'}"
            ),
        )

    if window.contains(nozzle_c=nozzle_c, bed_c=bed_c):
        return MaterialCheckResult(
            passed=True,
            material=material,
            nozzle_c=nozzle_c,
            bed_c=bed_c,
            window=window,
            reason="within window",
        )

    why_parts: list[str] = []
    if not (window.nozzle_min_c <= nozzle_c <= window.nozzle_max_c):
        why_parts.append(
            f"nozzle {nozzle_c:.1f}C out of [{window.nozzle_min_c:.0f},"
            f"{window.nozzle_max_c:.0f}]"
        )
    if not (window.bed_min_c <= bed_c <= window.bed_max_c):
        why_parts.append(
            f"bed {bed_c:.1f}C out of [{window.bed_min_c:.0f},"
            f"{window.bed_max_c:.0f}]"
        )
    reason = "; ".join(why_parts)

    if _override_active(env):
        LOG.warning(
            "material_window: %s OUT OF WINDOW (%s) — OVERRIDE active, allowing",
            material,
            reason,
        )
        return MaterialCheckResult(
            passed=True,
            material=material,
            nozzle_c=nozzle_c,
            bed_c=bed_c,
            window=window,
            reason=reason,
            overridden=True,
        )

    return MaterialCheckResult(
        passed=False,
        material=material,
        nozzle_c=nozzle_c,
        bed_c=bed_c,
        window=window,
        reason=reason,
    )


def build_violation_payload(
    *,
    job_id: str,
    printer_id: str,
    result: MaterialCheckResult,
) -> dict[str, Any]:
    """Build the ``safety.violation`` payload for a failed material check."""
    return {
        "kind": "safety.violation",
        "gate": "safety.material_temperature_window",
        "job_id": job_id,
        "printer_id": printer_id,
        "result": result.to_dict(),
    }


__all__ = [
    "MATERIAL_DB_DEFAULT_PATH",
    "MATERIAL_DB_USER_PATH",
    "OVERRIDE_ENV_VAR",
    "MaterialCheckResult",
    "MaterialDB",
    "MaterialWindow",
    "build_violation_payload",
    "check_material_window",
    "load_material_db",
]
