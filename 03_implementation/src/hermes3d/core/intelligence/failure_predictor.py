"""Failure predictor.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §36 (Failure Prediction)

Computes a failure-probability estimate for a proposed print before it
starts. The prediction blends three signals:

  1. Per-printer historical failure rate (from PrintHistory)
  2. Per-material historical failure rate
  3. Known failure-pattern skills with matching scope

The output is a calibrated probability and a list of citations explaining
the score. The dispatcher / multi-agent critic can use this to bias
selection or warn the user before committing filament.

Design: a deliberately simple Bayesian-flavored blend. Not ML —
real-farm datasets are too small for ML; this is a rule-based estimator
that's auditable and tunable.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from hermes3d.core.farm.print_history import (
    PrintHistoryReader,
    aggregate_metrics,
    default_print_history_reader,
)
from hermes3d.core.memory import SkillKind, SkillStore

# Number of prints below which a printer's success rate is too noisy
# to weigh on its own.
MIN_EVIDENCE_PRINTS = 5

# Default baseline failure rate when we have no data at all (~industry
# average for hobby 3D printing).
DEFAULT_BASELINE_FAILURE_RATE = 0.10


@dataclass
class FailureForecast:
    """Per-print failure-probability estimate."""

    printer_id: str
    material: str
    failure_probability: float
    confidence: str  # "low" | "medium" | "high"
    citations: list[str] = field(default_factory=list)
    components: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _printer_component(
    history: PrintHistoryReader | None, printer_id: str
) -> tuple[float, int, str | None]:
    if history is None:
        return DEFAULT_BASELINE_FAILURE_RATE, 0, None
    metrics = aggregate_metrics(history)
    pa = metrics.per_printer.get(printer_id)
    if pa is None or pa.total_prints == 0:
        return DEFAULT_BASELINE_FAILURE_RATE, 0, None
    rate = 1.0 - pa.success_rate
    citation = (
        f"PrintHistory[{printer_id}]: {pa.failed} fails / {pa.successful + pa.failed} attempts"
    )
    return rate, pa.total_prints, citation


def _material_component(
    history: PrintHistoryReader | None, material: str
) -> tuple[float, int, str | None]:
    if history is None:
        return DEFAULT_BASELINE_FAILURE_RATE, 0, None
    metrics = aggregate_metrics(history)
    ma = metrics.per_material.get(material.upper())
    if ma is None or ma.total_prints == 0:
        return DEFAULT_BASELINE_FAILURE_RATE, 0, None
    rate = 1.0 - (ma.successful / ma.total_prints)
    citation = f"PrintHistory[material={material}]: {ma.successful}/{ma.total_prints} successful"
    return rate, ma.total_prints, citation


def _skill_component(
    skills: SkillStore | None, printer_id: str, material: str
) -> tuple[float | None, list[str]]:
    if skills is None:
        return None, []
    matches = skills.lookup(
        kind=SkillKind.FAILURE_PATTERN,
        printer_id=printer_id,
        material=material,
        min_confidence=0.4,
    )
    if not matches:
        return None, []
    # The most-specific, highest-confidence skill wins
    top = matches[0]
    rate = float(top.body.get("observed_failure_rate", 0.5))
    citation = (
        f"Skill[{top.skill_id[:8]}] '{top.name}' "
        f"(confidence={top.confidence:.2f}): "
        f"observed_failure_rate={rate:.2f}"
    )
    return rate, [citation]


def predict_failure(
    *,
    printer_id: str,
    material: str,
    history: PrintHistoryReader | None = None,
    skills: SkillStore | None = None,
) -> FailureForecast:
    """Blend printer-history, material-history, and skill signals.

    Weighting:
      - skill match (specific failure pattern): 0.50 if present
      - printer history (when N >= MIN_EVIDENCE_PRINTS): 0.30
      - material history (when N >= MIN_EVIDENCE_PRINTS): 0.20
      - remaining weight rolls onto the baseline 10% failure rate.
    """
    components: dict[str, float] = {}
    citations: list[str] = []
    weight_used = 0.0
    weighted_sum = 0.0
    history = history or default_print_history_reader()

    skill_rate, skill_cites = _skill_component(skills, printer_id, material)
    if skill_rate is not None:
        weighted_sum += 0.50 * skill_rate
        weight_used += 0.50
        components["skill"] = skill_rate
        citations.extend(skill_cites)

    p_rate, p_n, p_cite = _printer_component(history, printer_id)
    if p_n >= MIN_EVIDENCE_PRINTS:
        weighted_sum += 0.30 * p_rate
        weight_used += 0.30
        components["printer_history"] = p_rate
        if p_cite:
            citations.append(p_cite)

    m_rate, m_n, m_cite = _material_component(history, material)
    if m_n >= MIN_EVIDENCE_PRINTS:
        weighted_sum += 0.20 * m_rate
        weight_used += 0.20
        components["material_history"] = m_rate
        if m_cite:
            citations.append(m_cite)

    # Roll remaining weight onto baseline
    if weight_used < 1.0:
        weighted_sum += (1.0 - weight_used) * DEFAULT_BASELINE_FAILURE_RATE
        components["baseline"] = DEFAULT_BASELINE_FAILURE_RATE

    prob = max(0.0, min(1.0, weighted_sum))

    # Confidence labelling
    if weight_used >= 0.7:
        confidence = "high"
    elif weight_used >= 0.3:
        confidence = "medium"
    else:
        confidence = "low"

    return FailureForecast(
        printer_id=printer_id,
        material=material,
        failure_probability=round(prob, 3),
        confidence=confidence,
        citations=citations,
        components={k: round(v, 3) for k, v in components.items()},
    )


__all__ = [
    "DEFAULT_BASELINE_FAILURE_RATE",
    "MIN_EVIDENCE_PRINTS",
    "FailureForecast",
    "predict_failure",
]
