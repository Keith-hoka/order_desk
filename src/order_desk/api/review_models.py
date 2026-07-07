"""Response/request schemas for the review API (Phase 7)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from order_desk.review.priority import ReviewStatus


class FieldFlagOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    raw_confidence: float
    calibrated_confidence: float
    in_band: bool


class ReviewItemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    subject: str
    body: str
    extraction: dict | None
    field_flags: list[FieldFlagOut]
    asks: list[str]
    violations: list[str]
    priority: float
    status: ReviewStatus
    edits: dict[str, str]


class ReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewStatus  # approved | edited | rejected
    edits: dict[str, str] = {}
