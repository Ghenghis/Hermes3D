from __future__ import annotations

from collections.abc import Iterable

from hermes3d.core.memory.skill_store import Skill, SkillKind, SkillScope
from hermes3d.core.slicer.profile_generator import generate_profile


class FakeSkillStoreReader:
    def __init__(self, rows: Iterable[Skill]) -> None:
        self._rows = list(rows)

    def by_printer(self, printer_id: str) -> Iterable[Skill]:
        return [s for s in self._rows if s.scope.matches(printer_id=printer_id)]

    def by_material(self, material: str) -> Iterable[Skill]:
        return [s for s in self._rows if s.scope.matches(material=material)]

    def by_quality(self, quality_level: str) -> Iterable[Skill]:
        return [s for s in self._rows if s.scope.matches(quality_level=quality_level)]

    def reinforced_only(self, *, min_score: float = 0.0) -> Iterable[Skill]:
        return [s for s in self._rows if s.confidence >= min_score]

    def lookup(
        self,
        *,
        kind: SkillKind,
        printer_id: str | None = None,
        material: str | None = None,
        quality_level: str | None = None,
        hour_of_day: int | None = None,
        min_confidence: float = 0.0,
    ) -> list[Skill]:
        return [
            s
            for s in self._rows
            if s.skill_kind == kind
            and s.confidence >= min_confidence
            and s.scope.matches(
                printer_id=printer_id,
                material=material,
                quality_level=quality_level,
                hour_of_day=hour_of_day,
            )
        ]


def _skill(
    skill_id: str,
    *,
    name: str,
    scope: SkillScope,
    body: dict[str, object],
    confidence: float,
) -> Skill:
    return Skill(
        skill_id=skill_id,
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name=name,
        scope=scope,
        body=body,
        confidence=confidence,
        evidence_count=3,
        source="agent_observed",
    )


def test_profile_generator_uses_injected_skill_reader_for_overrides() -> None:
    baseline = generate_profile(
        printer_id="flsun_t1_a",
        material="PLA",
        quality_level="normal",
        skills=None,
    )
    reader = FakeSkillStoreReader(
        [
            _skill(
                "pla-fill",
                name="PLA reinforced fill",
                scope=SkillScope(material="PLA", quality_level="normal"),
                body={"fill_density": "32%"},
                confidence=0.82,
            ),
            _skill(
                "flsun-temp",
                name="FLSUN first-layer heat",
                scope=SkillScope(
                    printer_id="flsun_t1_a",
                    material="PLA",
                    quality_level="normal",
                ),
                body={"slicer_setting": "first_layer_temperature", "value": 224},
                confidence=0.91,
            ),
            _skill(
                "weak",
                name="Weak draft-only tweak",
                scope=SkillScope(material="PLA", quality_level="draft"),
                body={"perimeter_speed": "1"},
                confidence=0.39,
            ),
        ]
    )

    generated = generate_profile(
        printer_id="flsun_t1_a",
        material="PLA",
        quality_level="normal",
        skills=reader,
    )

    assert baseline.settings["fill_density"] == "20%"
    assert baseline.settings["first_layer_temperature"] != "224"
    assert baseline.applied_skills == []

    assert generated.profile_id == baseline.profile_id
    assert generated.settings["fill_density"] == "32%"
    assert generated.settings["first_layer_temperature"] == "224"
    assert generated.settings["perimeter_speed"] == baseline.settings["perimeter_speed"]
    assert any("PLA reinforced fill" in s for s in generated.applied_skills)
    assert any("FLSUN first-layer heat" in s for s in generated.applied_skills)
    assert all("Weak draft-only tweak" not in s for s in generated.applied_skills)
    assert "first_layer_temperature = 224" in generated.to_ini()
