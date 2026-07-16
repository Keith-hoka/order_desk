"""Exception priority: what most needs a human (Phase 7).

Integrates the signals every prior phase produced into a single priority for
review triage. The actionable confidence band is raw [0.80, 0.95] -- Phase 4
found fields there are only ~40% correct (the model is moderately sure but
often wrong), while lower-confidence fields were all correct and higher ones
are trustworthy. So band-membership, not lowest confidence, flags a field.

Priority combines three signals, weighted so a policy violation outranks an
ask, which outranks a band field: violations are certainly wrong, asks are the
model's own uncertainty flags (blend / reply-history), band fields are the
statistical risk. The calibrated confidence (Phase 4 isotonic) is carried for
display only -- it is in-sample and flat across the sparse [0.72, 0.95] region,
so it informs the reviewer but does not drive ranking (decision B).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from order_desk.calibration import IsotonicCalibrator
from order_desk.pipeline.policy import PipelineState

BAND_LO = 0.80
BAND_HI = 0.95

# weights: violation > ask > band field
W_VIOLATION = 10.0
W_ASK = 4.0
W_BAND = 1.0


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


@dataclass
class FieldFlag:
    path: str
    raw_confidence: float
    calibrated_confidence: float
    in_band: bool


@dataclass
class ReviewItem:
    id: str
    subject: str
    body: str
    extraction: dict | None
    field_flags: list[FieldFlag]
    asks: list[str]
    violations: list[str]
    priority: float
    status: ReviewStatus = ReviewStatus.PENDING
    edits: dict[str, str] = field(default_factory=dict)
    org_id: str = "org-demo"
    # recorded fulfilment outcome (FulfillResult shape); an order already
    # submitted to the ERP must not be submitted again on a later approve
    fulfillment: dict | None = None

    @property
    def band_field_count(self) -> int:
        return sum(1 for f in self.field_flags if f.in_band)


def field_flags(confidence: dict[str, float], calibrator: IsotonicCalibrator) -> list[FieldFlag]:
    """Per-field raw + calibrated confidence and band membership."""
    flags = []
    for path, raw in confidence.items():
        flags.append(
            FieldFlag(
                path=path,
                raw_confidence=raw,
                calibrated_confidence=calibrator.calibrate(raw),
                in_band=BAND_LO <= raw <= BAND_HI,
            )
        )
    return flags


def priority_score(band_count: int, n_asks: int, n_violations: int) -> float:
    """Weighted combination; violation > ask > band field."""
    return W_VIOLATION * n_violations + W_ASK * n_asks + W_BAND * band_count


def build_review_item(
    state: PipelineState, calibrator: IsotonicCalibrator, item_id: str
) -> ReviewItem:
    flags = field_flags(state.confidence, calibrator)
    band_count = sum(1 for f in flags if f.in_band)
    priority = priority_score(band_count, len(state.asks), len(state.violations))
    return ReviewItem(
        id=item_id,
        subject=state.subject,
        body=state.body,
        extraction=state.extraction.model_dump() if state.extraction else None,
        field_flags=flags,
        asks=list(state.asks),
        violations=list(state.violations),
        priority=priority,
    )


def sort_queue(items: list[ReviewItem]) -> list[ReviewItem]:
    """Highest priority first; stable on ties by id for determinism."""
    return sorted(items, key=lambda it: (-it.priority, it.id))
