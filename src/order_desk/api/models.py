"""Request/response schemas for the extraction API (Phase 4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from order_desk.schemas import ExtractedOrder


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class ExtractMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    adapter: str
    latency_s: float
    input_tokens: int
    output_tokens: int
    parse_repaired: bool
    overall_confidence: float


class ExtractResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction: ExtractedOrder
    confidence: dict[str, float]
    meta: ExtractMeta
