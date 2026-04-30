"""Print quality scoring.

Every completed print is scored on a 0..1 scale across multiple dimensions.
The scores feed two consumers:

1. The skill memory's ``reinforce``/``weaken`` API (so good outcomes promote
   the parameters that produced them).
2. The print history aggregate (so the failure predictor can compute a real
   per-printer / per-material reliability number).

Scoring is heuristic and deterministic. It blends:
  - Slicer prediction confidence (g-code analyzer risk flags)
  - User feedback (1-5 star)
  - Mid-print events (pauses, restarts, filament changes)
  - Time deviation (actual vs predicted)

The output is intentionally explainable: every dimension carries a list of
``reason`` strings the dashboard can show.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class PrintOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"  # finished but with visible defects
    FAILED = "failed"    # mid-print failure, manual abort, etc.
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class QualityDimension:
    name: str
    score: float  # 0..1
    weight: float  # 0..1
    reasons: list[str] = field(default_factory=list)


@dataclass
class QualityReport:
    overall_score: float  # 0..1
    confidence: float  # 0..1 — how trustworthy the score is
    outcome: PrintOutcome
    dimensions: list[QualityDimension]
    generated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "overall_score": round(self.overall_score, 4),
            "confidence": round(self.confidence, 4),
            "outcome": self.outcome.value,
            "dimensions": [
                {
                    "name": d.name,
                    "score": round(d.score, 4),
                    "weight": round(d.weight, 4),
                    "reasons": list(d.reasons),
                }
                for d in self.dimensions
            ],
            "generated_at": self.generated_at,
        }


@dataclass
class ScoringInput:
    """Everything needed to score a finished print."""

    outcome: PrintOutcome
    predicted_duration_seconds: float | None = None
    actual_duration_seconds: float | None = None
    pause_count: int = 0
    filament_change_count: int = 0
    user_rating_1_to_5: int | None = None  # None means no feedback yet
    gcode_risk_flags: list[str] = field(default_factory=list)
    obico_pause_count: int = 0
    layer_shift_detected: bool = False
    spaghetti_detected: bool = False
    notes: str | None = None


# Weights tuned so that a perfect successful print without feedback gets ~0.85
# (we leave headroom for the user-rating dimension to push toward 1.0).
_DIMENSION_WEIGHTS = {
    "outcome": 0.35,
    "duration_accuracy": 0.10,
    "stability": 0.20,
    "user_feedback": 0.20,
    "automated_signals": 0.15,
}


def _score_outcome(outcome: PrintOutcome) -> tuple[float, list[str]]:
    if outcome == PrintOutcome.SUCCESS:
        return 1.0, ["finished without manual intervention"]
    if outcome == PrintOutcome.PARTIAL:
        return 0.55, ["finished with visible defects"]
    if outcome == PrintOutcome.FAILED:
        return 0.05, ["print failed before completion"]
    if outcome == PrintOutcome.CANCELLED:
        return 0.20, ["user cancelled mid-print"]
    return 0.50, ["outcome unknown — neutral score"]


def _score_duration_accuracy(
    predicted: float | None, actual: float | None
) -> tuple[float, list[str], float]:
    """Return (score, reasons, confidence_factor)."""
    if predicted is None or actual is None or predicted <= 0:
        return 0.5, ["no duration data available"], 0.5
    ratio = actual / predicted
    if 0.9 <= ratio <= 1.1:
        return 1.0, [f"actual duration within ±10% (ratio={ratio:.2f})"], 1.0
    if 0.75 <= ratio <= 1.25:
        return 0.7, [f"actual duration within ±25% (ratio={ratio:.2f})"], 1.0
    if 0.5 <= ratio <= 1.5:
        return 0.4, [f"actual duration within ±50% (ratio={ratio:.2f})"], 1.0
    return 0.1, [f"actual duration far from predicted (ratio={ratio:.2f})"], 1.0


def _score_stability(pauses: int, filament_changes: int, obico_pauses: int) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 1.0
    if pauses > 0:
        reasons.append(f"manual pauses: {pauses}")
        score -= 0.15 * pauses
    if obico_pauses > 0:
        reasons.append(f"obico-triggered pauses: {obico_pauses}")
        score -= 0.20 * obico_pauses
    if filament_changes > 0:
        reasons.append(f"unexpected filament changes: {filament_changes}")
        score -= 0.10 * filament_changes
    if not reasons:
        reasons.append("no interruptions")
    return max(0.0, score), reasons


def _score_user_feedback(rating: int | None) -> tuple[float, list[str], float]:
    if rating is None:
        return 0.5, ["no user feedback yet"], 0.0
    rating = max(1, min(5, rating))
    score = (rating - 1) / 4.0  # 1->0, 5->1
    return score, [f"user rated {rating}/5"], 1.0


def _score_automated_signals(
    risk_flags: list[str], layer_shift: bool, spaghetti: bool
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 1.0
    if layer_shift:
        reasons.append("layer shift detected by computer vision")
        score -= 0.5
    if spaghetti:
        reasons.append("spaghetti / extrusion failure detected")
        score -= 0.6
    for flag in risk_flags:
        reasons.append(f"slicer risk flag: {flag}")
        score -= 0.05
    if not reasons:
        reasons.append("no automated risk signals")
    return max(0.0, score), reasons


def score_print(inp: ScoringInput) -> QualityReport:
    """Compute the quality report for a single print."""
    dims: list[QualityDimension] = []
    confidence_factors: list[float] = []

    s, r = _score_outcome(inp.outcome)
    dims.append(QualityDimension("outcome", s, _DIMENSION_WEIGHTS["outcome"], r))
    confidence_factors.append(0.95 if inp.outcome != PrintOutcome.UNKNOWN else 0.5)

    s, r, cf = _score_duration_accuracy(
        inp.predicted_duration_seconds, inp.actual_duration_seconds
    )
    dims.append(QualityDimension("duration_accuracy", s, _DIMENSION_WEIGHTS["duration_accuracy"], r))
    confidence_factors.append(cf)

    s, r = _score_stability(inp.pause_count, inp.filament_change_count, inp.obico_pause_count)
    dims.append(QualityDimension("stability", s, _DIMENSION_WEIGHTS["stability"], r))
    confidence_factors.append(0.9)

    s, r, cf = _score_user_feedback(inp.user_rating_1_to_5)
    dims.append(QualityDimension("user_feedback", s, _DIMENSION_WEIGHTS["user_feedback"], r))
    confidence_factors.append(cf)

    s, r = _score_automated_signals(
        inp.gcode_risk_flags, inp.layer_shift_detected, inp.spaghetti_detected
    )
    dims.append(QualityDimension("automated_signals", s, _DIMENSION_WEIGHTS["automated_signals"], r))
    confidence_factors.append(0.7)

    overall = sum(d.score * d.weight for d in dims)
    # Renormalize against weights actually used (all weights sum to 1.0 by design).
    total_weight = sum(d.weight for d in dims)
    if total_weight > 0:
        overall = overall / total_weight

    confidence = sum(confidence_factors) / max(1, len(confidence_factors))

    return QualityReport(
        overall_score=round(overall, 4),
        confidence=round(confidence, 4),
        outcome=inp.outcome,
        dimensions=dims,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


__all__ = [
    "PrintOutcome",
    "QualityDimension",
    "QualityReport",
    "ScoringInput",
    "score_print",
]
