"""Review API endpoints (Phase 7). Guarded by the same JWT auth as /extract."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from order_desk.api.auth import Principal, require_auth
from order_desk.api.review_models import (
    ExtractRequest,
    FieldFlagOut,
    FulfillmentOut,
    InboxExtractRequest,
    ReviewAction,
    ReviewItemOut,
)
from order_desk.flywheel.corrections import apply_edits
from order_desk.review.priority import ReviewItem, ReviewStatus

REQUIRED_FIELDS = (
    "customer_po_text",
    "delivery_address_text",
    "buyer_name_text",
    "requested_date_text",
)


def _missing_required_fields(extraction: dict) -> list[str]:
    """Field paths still empty after the reviewer's corrections.

    An approve is a claim that the order is complete; every header field and
    every remaining line's product and quantity must be filled to make it, and
    an order with no lines at all is not an order.
    """
    missing = [f for f in REQUIRED_FIELDS if not extraction.get(f)]
    if not extraction.get("line_items"):
        missing.append("line_items")
    for i, li in enumerate(extraction.get("line_items", [])):
        if not li.get("product_text"):
            missing.append(f"line_items.{i}.product_text")
        if li.get("quantity") in (None, ""):
            missing.append(f"line_items.{i}.quantity")
    return missing


review_router = APIRouter(prefix="/exceptions")


def _get_store(request: Request):
    store = getattr(request.app.state, "review_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="review store not configured")
    return store


def _to_out(item: ReviewItem) -> ReviewItemOut:
    return ReviewItemOut(
        id=item.id,
        subject=item.subject,
        body=item.body,
        extraction=item.extraction,
        field_flags=[FieldFlagOut(**vars(f)) for f in item.field_flags],
        asks=item.asks,
        violations=item.violations,
        priority=item.priority,
        status=item.status,
        edits=item.edits,
        fulfillment=FulfillmentOut(**item.fulfillment) if item.fulfillment else None,
    )


def _org_of(principal: Principal | None) -> str | None:
    """Scope requests to the caller's org; None means no tenant filtering."""
    return principal.org_id if principal is not None else None


@review_router.get("", response_model=list[ReviewItemOut])
def list_exceptions(
    request: Request, principal: Principal | None = Depends(require_auth)
) -> list[ReviewItemOut]:
    store = _get_store(request)
    return [_to_out(it) for it in store.list_items(org_id=_org_of(principal))]


@review_router.post("/extract", response_model=ReviewItemOut)
def live_extract(
    req: ExtractRequest, request: Request, principal: Principal | None = Depends(require_auth)
) -> ReviewItemOut:
    """Run one pasted email through the live pipeline into the caller's queue."""
    extractor = getattr(request.app.state, "live_extractor", None)
    if extractor is None:
        raise HTTPException(
            status_code=503,
            detail="live extraction not configured (needs VLLM_BASE_URL and OPENAI_API_KEY)",
        )
    store = _get_store(request)
    item_id = f"EXC-{uuid.uuid4().hex[:6].upper()}"
    try:
        item = extractor.extract(req.subject, req.body, item_id)
    except Exception as exc:  # surface pipeline failures as a gateway error
        raise HTTPException(status_code=502, detail=f"extraction failed: {exc}") from exc
    if principal is not None and principal.org_id is not None:
        item.org_id = principal.org_id
    store.add_item(item)
    return _to_out(item)


# each mailbox pull costs one OpenAI + one Modal call per email; cap the batch
INBOX_PULL_LIMIT = 10


@review_router.post("/extract-inbox", response_model=list[ReviewItemOut])
def extract_inbox(
    req: InboxExtractRequest,
    request: Request,
    principal: Principal | None = Depends(require_auth),
) -> list[ReviewItemOut]:
    """Pull a mailbox's recent unseen emails through the pipeline.

    A reviewer may supply their own mailbox (host + address + app password);
    the credentials are used for this one connection and never stored. With no
    password the server-configured mailbox (IMAP_* environment) is used, and
    the entered address must match it -- an address alone is never enough to
    reach an arbitrary inbox.
    """
    extractor = getattr(request.app.state, "live_extractor", None)
    if extractor is None:
        raise HTTPException(
            status_code=503,
            detail="live extraction not configured (needs VLLM_BASE_URL and OPENAI_API_KEY)",
        )
    settings = request.app.state.settings
    if req.password:
        if not req.host:
            raise HTTPException(status_code=400, detail="host is required with a password")
        host, username, password, mailbox = req.host, req.address, req.password, req.mailbox
    else:
        if not (settings.imap_host and settings.imap_username and settings.imap_password):
            raise HTTPException(
                status_code=503,
                detail="no mailbox: enter its host and app password, "
                "or configure IMAP_HOST/IMAP_USERNAME/IMAP_PASSWORD server-side",
            )
        if req.address.strip().lower() != settings.imap_username.lower():
            raise HTTPException(
                status_code=400,
                detail=f"'{req.address}' is not the configured mailbox "
                f"({settings.imap_username}); enter its host and app password to use it",
            )
        host, username, password, mailbox = (
            settings.imap_host,
            settings.imap_username,
            settings.imap_password,
            settings.imap_mailbox,
        )
    store = _get_store(request)

    from order_desk.ingest.source import ImapSource

    source = ImapSource(host, username, password, mailbox=mailbox)
    try:
        raws = list(source.fetch(limit=INBOX_PULL_LIMIT))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"mailbox fetch failed: {exc}") from exc

    created: list[ReviewItemOut] = []
    errors: list[str] = []
    for raw in raws:
        item_id = f"EXC-{uuid.uuid4().hex[:6].upper()}"
        try:
            item = extractor.extract_raw(raw, item_id)
        except Exception as exc:  # one bad email must not sink the batch
            errors.append(str(exc))
            continue
        if principal is not None and principal.org_id is not None:
            item.org_id = principal.org_id
        store.add_item(item)
        created.append(_to_out(item))
    if raws and not created:
        raise HTTPException(status_code=502, detail=f"extraction failed: {errors[0]}")
    return created


# the 66 committed human-test emails carry 4-digit ids (EXC-0000..EXC-0065);
# live-extracted items carry 6-hex ids and are the deletable ones
SEED_ID = re.compile(r"^EXC-\d{4}$")


@review_router.delete("/{item_id}")
def delete_exception(
    item_id: str, request: Request, principal: Principal | None = Depends(require_auth)
) -> dict:
    """Remove a live-extracted item; the committed seed queue is off limits."""
    store = _get_store(request)
    item = store.get_item(item_id, org_id=_org_of(principal))
    if item is None:
        raise HTTPException(status_code=404, detail="exception not found")
    if SEED_ID.fullmatch(item.id):
        raise HTTPException(status_code=403, detail="seed items cannot be deleted")
    store.delete_item(item_id)
    return {"deleted": item_id}


@review_router.get("/{item_id}", response_model=ReviewItemOut)
def get_exception(
    item_id: str, request: Request, principal: Principal | None = Depends(require_auth)
) -> ReviewItemOut:
    store = _get_store(request)
    item = store.get_item(item_id, org_id=_org_of(principal))
    if item is None:
        raise HTTPException(status_code=404, detail="exception not found")
    return _to_out(item)


@review_router.post("/{item_id}/review", response_model=ReviewItemOut)
def submit_review(
    item_id: str,
    action: ReviewAction,
    request: Request,
    principal: Principal | None = Depends(require_auth),
) -> ReviewItemOut:
    store = _get_store(request)

    # approving claims the order is complete -- validate BEFORE recording the
    # decision, so a blocked approve leaves the item untouched
    if action.action == ReviewStatus.APPROVED:
        current = store.get_item(item_id, org_id=_org_of(principal))
        if current is None:
            raise HTTPException(status_code=404, detail="exception not found")
        # a routed-away item (no extraction) validates against the empty
        # skeleton -- approvable only once the reviewer has built the order
        missing = _missing_required_fields(apply_edits(current.extraction, current.edits))
        if missing:
            raise HTTPException(
                status_code=422,
                detail={"error": "required fields missing", "missing": missing},
            )

    item = store.submit_review(item_id, action.action, action.edits, org_id=_org_of(principal))
    if item is None:
        raise HTTPException(status_code=404, detail="exception not found")

    out = _to_out(item)
    sink = getattr(request.app.state, "order_sink", None)
    notifier = getattr(request.app.state, "notifier", None)
    # two-step flow: saving corrections (EDITED) only records them; APPROVED is
    # the send. Idempotent per version -- the same corrections never go out
    # twice; new corrections on an already-sent order go out as an amendment.
    prior = item.fulfillment
    prior_submitted = bool(prior and prior.get("submitted"))
    # legacy records are stamped with for_edits at store load, so this compares
    # what was sent against what the reviewer has corrected since
    already_sent = prior_submitted and prior.get("for_edits") == item.edits
    if (
        action.action == ReviewStatus.APPROVED
        and sink is not None
        and notifier is not None
        and not already_sent
    ):
        from order_desk.fulfillment.fulfill import fulfill_order

        # an edited item goes downstream as the reviewer corrected it, not as
        # the model first extracted it; a routed-away item goes downstream as
        # the order the reviewer built from scratch
        extraction = apply_edits(item.extraction, item.edits)
        amends = prior.get("order_id") if prior_submitted else None

        try:
            fr = fulfill_order(extraction, sink, notifier, amends=amends)
            recorded = {
                "submitted": fr.submitted,
                "order_id": fr.order_id,
                "reason": fr.reason,
                "unresolved": fr.unresolved,
                "issues": fr.issues,
                "amends": amends,
                "for_edits": dict(item.edits),
            }
            # a failed amendment must not erase the receipt of the order that
            # IS in the ERP; report it live but keep the original on record
            if fr.submitted or not prior_submitted:
                store.record_fulfillment(item.id, recorded)
            out.fulfillment = FulfillmentOut(**recorded)
        except Exception as exc:  # fulfillment failure must not fail the approval
            out.fulfillment = FulfillmentOut(
                submitted=False,
                order_id=None,
                reason=f"error: {exc}",
                unresolved=[],
            )
    return out
