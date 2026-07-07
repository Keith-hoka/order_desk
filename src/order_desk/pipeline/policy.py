"""Routing policy and pipeline state (Phase 5).

Deterministic routing: each EmailClass maps to exactly one RouteDecision,
so routing accuracy is measurable against gold with no new annotation
(route is a pure function of class). Only order-bearing classes reach the
learned extraction node; the rest take deterministic paths.

Blended order-plus-question emails (the fine-tune's known over-extraction
case) are classified as orders and extracted normally, then flagged in
validation -- strategy A. The blend signal is a product-inquiry heuristic
("do you stock", "do you have"), not a bare question mark: polite questions
("could you confirm?") do not cause over-extraction, only product inquiries
do. This heuristic has no gold, so it is surfaced as an ask and validated
qualitatively (never scored for precision/recall).
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from order_desk.schemas import EmailClass, ExtractedOrder


class RouteDecision(StrEnum):
    EXTRACT = "extract"  # order-bearing -> call the learned node
    CANCEL = "cancel"  # cancellation -> pull the referenced PO
    INQUIRY = "inquiry"  # question only -> mark for downstream handling
    DISCARD = "discard"  # not relevant -> archive


_ROUTE_BY_CLASS: dict[EmailClass, RouteDecision] = {
    EmailClass.NEW_ORDER: RouteDecision.EXTRACT,
    EmailClass.AMENDMENT: RouteDecision.EXTRACT,
    EmailClass.CANCELLATION: RouteDecision.CANCEL,
    EmailClass.INQUIRY: RouteDecision.INQUIRY,
    EmailClass.OTHER: RouteDecision.DISCARD,
}

# Product-inquiry patterns that signal a blended order+question (over-extraction risk).
# Deliberately narrow: aimed at product/stock questions, not polite phrasing.
_PRODUCT_INQUIRY_PATTERNS = [
    r"\bdo you (?:stock|have|carry|supply|sell)\b",
    r"\bdo you offer\b",
    r"\bis there a\b",
    r"\bare there any\b",
    r"\bwhat(?:'s| is) the (?:price|cost|lead time|moq)\b",
    r"\bcan you (?:source|get|supply)\b",
]
_INQUIRY_RE = re.compile("|".join(_PRODUCT_INQUIRY_PATTERNS), re.IGNORECASE)


def route_for_class(email_class: EmailClass) -> RouteDecision:
    """Deterministic class -> route mapping (the policy core)."""
    return _ROUTE_BY_CLASS[email_class]


def detect_product_inquiry(body: str) -> bool:
    """Heuristic blend signal: a product/stock question within the email body."""
    return _INQUIRY_RE.search(body) is not None


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_class: EmailClass
    confidence: float = 1.0


class PipelineState(BaseModel):
    """State threaded through the pipeline graph."""

    model_config = ConfigDict(extra="forbid")

    subject: str
    body: str
    classification: Classification | None = None
    route: RouteDecision | None = None
    extraction: ExtractedOrder | None = None
    confidence: dict[str, float] = Field(default_factory=dict)
    asks: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)


def policy_violations(state: PipelineState) -> list[str]:
    """Deterministic policy checks: does the state obey the routing contract?"""
    v: list[str] = []
    route = state.route
    if route is None:
        v.append("no route assigned")
        return v
    if route == RouteDecision.EXTRACT and state.extraction is None:
        v.append("EXTRACT route without an extraction")
    if route != RouteDecision.EXTRACT and state.extraction is not None:
        v.append(f"{route.value} route carries an unexpected extraction")
    return v
