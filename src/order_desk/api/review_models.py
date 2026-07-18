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


class FulfillmentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submitted: bool
    order_id: str | None
    reason: str
    unresolved: list[str]
    # quantity-rule violations (below_moq / above_max / missing) behind a hold
    issues: list[str] = []
    # original order id when this submission amended an already-sent order
    amends: str | None = None
    # notification is best-effort; a failed webhook is reported, not fatal
    notify_error: str | None = None
    # the edits snapshot this outcome fulfilled; lets a client tell whether the
    # current corrections have been sent or still await an approve
    for_edits: dict[str, str] | None = None


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
    fulfillment: FulfillmentOut | None = None


class ReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewStatus  # approved | edited | rejected
    edits: dict[str, str] = {}


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    body: str


class WebhookSettingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str  # empty string clears the webhook


class WebhookSettingOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    masked: str | None  # enough to recognise, never the full secret


class MailboxSettingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    address: str
    password: str  # all-empty clears the mailbox


class MailboxSettingOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    host: str | None
    address: str | None  # the password is never echoed back


class InboxExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str = ""  # empty: pull the org's configured mailbox
    # reviewer-supplied mailbox credentials: request-scoped, used for the one
    # connection and never stored. Empty password falls back to the mailbox
    # configured server-side (IMAP_* environment).
    host: str = ""
    password: str = ""
    mailbox: str = "INBOX"
