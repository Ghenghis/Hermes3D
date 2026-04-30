"""Self-improvement loop.

Hermes Agent's signature feature is that it gets better the longer it runs:
it observes outcomes, attributes them to (printer, material, parameter) tuples,
and either reinforces or weakens skills accordingly. Hermes3D-OS implements the
same loop on top of the existing skill memory + print history modules.

Given a stream of completed prints (with quality reports) it produces:

  - new skill candidates    (when an unfamiliar pattern shows clear signal)
  - reinforcement updates   (when an existing skill keeps producing wins)
  - weakening updates       (when an existing skill keeps producing losses)
  - retirement candidates   (when a skill's confidence drops below a floor)

The implementation is fully deterministic (no LLM calls) so it runs cheaply
inside the supervisor daemon every time a print finishes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from hermes3d.core.agents.quality_scorer import PrintOutcome, QualityReport
from hermes3d.core.memory.skill_store import (
    Skill,
    SkillKind,
    SkillScope,
    SkillStore,
)


# Score thresholds — anything above SUCCESS_FLOOR reinforces, below
# FAILURE_CEIL weakens. The band between is treated as ambiguous.
SUCCESS_FLOOR = 0.75
FAILURE_CEIL = 0.40

# Confidence at which a skill becomes a retirement candidate.
RETIREMENT_FLOOR = 0.15

# How many evidence points a candidate skill needs before it is created.
NEW_SKILL_MIN_EVIDENCE = 3

# How dominant a parameter-outcome correlation must be to spawn a new skill.
NEW_SKILL_MIN_DOMINANCE = 0.7


@dataclass
class PrintObservation:
    """One completed print, normalised for the loop."""

    printer_id: str
    material: str
    parameters: dict[str, object]  # the slicing parameters that were applied
    quality: QualityReport
    duration_seconds: float | None = None
    notes: str | None = None


@dataclass
class LoopUpdate:
    """One update produced by the loop."""

    kind: str  # "reinforce" | "weaken" | "create" | "retire"
    skill_id: str | None
    skill_name: str
    reason: str
    confidence_after: float
    evidence_after: int


@dataclass
class LoopReport:
    """Result of a single ``run_once`` invocation."""

    observations_processed: int
    reinforcements: list[LoopUpdate] = field(default_factory=list)
    weakenings: list[LoopUpdate] = field(default_factory=list)
    new_skills: list[LoopUpdate] = field(default_factory=list)
    retirements: list[LoopUpdate] = field(default_factory=list)

    @property
    def total_updates(self) -> int:
        return (
            len(self.reinforcements)
            + len(self.weakenings)
            + len(self.new_skills)
            + len(self.retirements)
        )


def _outcome_signal(quality: QualityReport) -> str:
    """Bucket each report into success / failure / ambiguous."""
    if quality.outcome == PrintOutcome.SUCCESS and quality.overall_score >= SUCCESS_FLOOR:
        return "success"
    if quality.outcome == PrintOutcome.FAILED or quality.overall_score <= FAILURE_CEIL:
        return "failure"
    if quality.outcome == PrintOutcome.PARTIAL and quality.overall_score < 0.6:
        return "failure"
    return "ambiguous"


def _matching_skills(store: SkillStore, obs: PrintObservation) -> list[Skill]:
    """Find existing skills whose scope matches this observation, across all kinds."""
    matches: list[Skill] = []
    seen: set[str] = set()
    for kind in SkillKind:
        for skill in store.lookup(
            kind=kind,
            printer_id=obs.printer_id,
            material=obs.material,
        ):
            if skill.skill_id not in seen:
                seen.add(skill.skill_id)
                matches.append(skill)
    return matches


def reinforce_or_weaken(store: SkillStore, observations: Iterable[PrintObservation]) -> LoopReport:
    """Walk a batch of observations and apply skill updates.

    The function never deletes a skill outright — retirement candidates are
    surfaced in the report; the caller decides whether to delete them.
    """
    obs_list = list(observations)
    report = LoopReport(observations_processed=len(obs_list))

    for obs in obs_list:
        signal = _outcome_signal(obs.quality)
        if signal == "ambiguous":
            continue

        for skill in _matching_skills(store, obs):
            if signal == "success":
                updated = store.reinforce(
                    skill.skill_id,
                    confidence_delta=0.05,
                    note=f"score={obs.quality.overall_score:.2f}",
                )
                report.reinforcements.append(
                    LoopUpdate(
                        kind="reinforce",
                        skill_id=updated.skill_id,
                        skill_name=updated.name,
                        reason=(
                            f"success on {obs.printer_id}/{obs.material} "
                            f"(score={obs.quality.overall_score:.2f})"
                        ),
                        confidence_after=updated.confidence,
                        evidence_after=updated.evidence_count,
                    )
                )
            else:
                updated = store.weaken(
                    skill.skill_id,
                    confidence_delta=0.10,
                    note=f"score={obs.quality.overall_score:.2f}",
                )
                report.weakenings.append(
                    LoopUpdate(
                        kind="weaken",
                        skill_id=updated.skill_id,
                        skill_name=updated.name,
                        reason=(
                            f"failure on {obs.printer_id}/{obs.material} "
                            f"(score={obs.quality.overall_score:.2f})"
                        ),
                        confidence_after=updated.confidence,
                        evidence_after=updated.evidence_count,
                    )
                )

    # Retirement pass — surface candidates without deleting.
    for skill in store.list():
        if skill.confidence <= RETIREMENT_FLOOR and skill.evidence_count >= 5:
            report.retirements.append(
                LoopUpdate(
                    kind="retire",
                    skill_id=skill.skill_id,
                    skill_name=skill.name,
                    reason=f"confidence {skill.confidence:.2f} below floor {RETIREMENT_FLOOR}",
                    confidence_after=skill.confidence,
                    evidence_after=skill.evidence_count,
                )
            )

    return report


def propose_new_skills(store: SkillStore, observations: Iterable[PrintObservation]) -> list[Skill]:
    """Look for unfamiliar parameter patterns that correlate with outcomes.

    Heuristic: group observations by (printer_id, material, parameter_key,
    parameter_value). If at least ``NEW_SKILL_MIN_EVIDENCE`` observations share
    the same key/value AND >= ``NEW_SKILL_MIN_DOMINANCE`` of them succeeded,
    propose a PARAMETER_OVERRIDE skill capturing that correlation.

    The proposals are added to the store and returned.
    """
    observations = list(observations)
    grouped: dict[tuple[str, str, str, str], list[PrintObservation]] = {}
    for obs in observations:
        for key, value in obs.parameters.items():
            grouped.setdefault((obs.printer_id, obs.material, key, str(value)), []).append(obs)

    existing_names = {s.name for s in store.list()}
    proposals: list[Skill] = []
    for (printer, material, key, value), group in grouped.items():
        if len(group) < NEW_SKILL_MIN_EVIDENCE:
            continue
        success_count = sum(1 for g in group if _outcome_signal(g.quality) == "success")
        dominance = success_count / len(group)
        if dominance < NEW_SKILL_MIN_DOMINANCE:
            continue

        name = f"{material}_on_{printer}_{key}={value}"
        if name in existing_names:
            continue

        confidence = min(0.85, 0.4 + 0.15 * (len(group) - NEW_SKILL_MIN_EVIDENCE))
        notes = (
            f"Setting {key}={value} for {material} on {printer} succeeded in "
            f"{success_count}/{len(group)} observed prints "
            f"(dominance={dominance:.0%})."
        )
        skill = store.add(
            skill_kind=SkillKind.PARAMETER_OVERRIDE,
            name=name,
            scope=SkillScope(printer_id=printer, material=material),
            body={"parameter": key, "value": value},
            confidence=confidence,
            source="self_improvement_loop",
            notes=notes,
        )
        # Keep evidence_count consistent with how many observations supported it.
        skill.evidence_count = len(group)
        store.save()
        proposals.append(skill)
    return proposals


def run_once(
    store: SkillStore,
    observations: Iterable[PrintObservation],
) -> LoopReport:
    """One full loop cycle: reinforce/weaken existing + propose new + return report."""
    obs_list = list(observations)
    report = reinforce_or_weaken(store, obs_list)
    for proposal in propose_new_skills(store, obs_list):
        report.new_skills.append(
            LoopUpdate(
                kind="create",
                skill_id=proposal.skill_id,
                skill_name=proposal.name,
                reason=proposal.notes or "auto-generated from outcome correlation",
                confidence_after=proposal.confidence,
                evidence_after=proposal.evidence_count,
            )
        )
    return report


__all__ = [
    "FAILURE_CEIL",
    "LoopReport",
    "LoopUpdate",
    "NEW_SKILL_MIN_DOMINANCE",
    "NEW_SKILL_MIN_EVIDENCE",
    "PrintObservation",
    "RETIREMENT_FLOOR",
    "SUCCESS_FLOOR",
    "propose_new_skills",
    "reinforce_or_weaken",
    "run_once",
]
