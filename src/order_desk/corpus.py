"""Mixed-class corpus assembly (step 1.6); materialization lands in step 1.7."""

from __future__ import annotations

import random
from collections import Counter, deque

from pydantic import BaseModel, ConfigDict, Field, model_validator

from order_desk.nonorder import (
    AmendmentScenario,
    CancellationScenario,
    InquiryScenario,
    OtherScenario,
    RenderedMessage,
    generate_amendments,
    generate_cancellations,
    generate_inquiries,
    generate_others,
    render_amendment,
    render_cancellation,
    render_inquiry,
    render_other,
    verify_amendment,
    verify_cancellation,
    verify_inquiry,
    verify_other,
)
from order_desk.renderer import RenderedEmail, render_email, verify_rendering
from order_desk.scenarios import OrderScenario, generate_scenarios
from order_desk.schemas import EmailClass

MixedItem = (
    OrderScenario | AmendmentScenario | CancellationScenario | InquiryScenario | OtherScenario
)


class ClassMix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weights: dict[EmailClass, float] = Field(
        default_factory=lambda: {
            EmailClass.NEW_ORDER: 0.70,
            EmailClass.AMENDMENT: 0.10,
            EmailClass.CANCELLATION: 0.05,
            EmailClass.INQUIRY: 0.10,
            EmailClass.OTHER: 0.05,
        }
    )

    @model_validator(mode="after")
    def integrity(self) -> ClassMix:
        if set(self.weights) != set(EmailClass):
            raise ValueError("mix must cover every EmailClass exactly once")
        if any(weight <= 0 for weight in self.weights.values()):
            raise ValueError("mix weights must be positive")
        return self


def derive_seed(seed: int, label: str) -> int:
    """Stable per-label sub-seed; avoids correlated streams across classes."""
    return random.Random(f"{seed}|{label}").getrandbits(63)


_GENERATORS = {
    EmailClass.NEW_ORDER: generate_scenarios,
    EmailClass.AMENDMENT: generate_amendments,
    EmailClass.CANCELLATION: generate_cancellations,
    EmailClass.INQUIRY: generate_inquiries,
    EmailClass.OTHER: generate_others,
}


def generate_corpus(n: int, seed: int, mix: ClassMix | None = None) -> list[MixedItem]:
    """Deterministically generate a mixed-class corpus for a given seed."""
    mix = mix or ClassMix()
    rng = random.Random(f"{seed}|class-mix")
    classes = list(mix.weights)
    assignment = rng.choices(classes, weights=[mix.weights[c] for c in classes], k=n)
    counts = Counter(assignment)
    pools = {
        cls: deque(_GENERATORS[cls](counts[cls], derive_seed(seed, cls.value)))
        for cls in classes
        if counts[cls]
    }
    return [pools[cls].popleft() for cls in assignment]


def render_item(item: MixedItem, seed: int) -> RenderedEmail | RenderedMessage:
    match item.email_class:
        case EmailClass.NEW_ORDER:
            return render_email(item, seed)
        case EmailClass.AMENDMENT:
            return render_amendment(item, seed)
        case EmailClass.CANCELLATION:
            return render_cancellation(item, seed)
        case EmailClass.INQUIRY:
            return render_inquiry(item, seed)
        case EmailClass.OTHER:
            return render_other(item, seed)
    raise AssertionError(item.email_class)


def verify_item(item: MixedItem, rendered: RenderedEmail | RenderedMessage) -> None:
    match item.email_class:
        case EmailClass.NEW_ORDER:
            verify_rendering(item, rendered)
        case EmailClass.AMENDMENT:
            verify_amendment(item, rendered)
        case EmailClass.CANCELLATION:
            verify_cancellation(item, rendered)
        case EmailClass.INQUIRY:
            verify_inquiry(item, rendered)
        case EmailClass.OTHER:
            verify_other(item, rendered)
