"""Review API endpoints (Phase 7). Guarded by the same JWT auth as /extract."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from order_desk.api.auth import Principal, require_auth
from order_desk.api.review_models import FieldFlagOut, ReviewAction, ReviewItemOut
from order_desk.review.priority import ReviewItem, ReviewStatus

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
    )


@review_router.get("", response_model=list[ReviewItemOut])
def list_exceptions(
    request: Request, principal: Principal | None = Depends(require_auth)
) -> list[ReviewItemOut]:
    store = _get_store(request)
    return [_to_out(it) for it in store.list_items()]


@review_router.get("/{item_id}", response_model=ReviewItemOut)
def get_exception(
    item_id: str, request: Request, principal: Principal | None = Depends(require_auth)
) -> ReviewItemOut:
    store = _get_store(request)
    item = store.get_item(item_id)
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
    item = store.submit_review(item_id, action.action, action.edits)
    if item is None:
        raise HTTPException(status_code=404, detail="exception not found")

    out = _to_out(item)
    sink = getattr(request.app.state, "order_sink", None)
    notifier = getattr(request.app.state, "notifier", None)
    if (
        action.action == ReviewStatus.APPROVED
        and sink is not None
        and notifier is not None
        and item.extraction
    ):
        from order_desk.api.review_models import FulfillmentOut
        from order_desk.fulfillment.fulfill import fulfill_order

        try:
            fr = fulfill_order(item.extraction, sink, notifier)
            out.fulfillment = FulfillmentOut(
                submitted=fr.submitted,
                order_id=fr.order_id,
                reason=fr.reason,
                unresolved=fr.unresolved,
            )
        except Exception as exc:  # fulfillment failure must not fail the approval
            out.fulfillment = FulfillmentOut(
                submitted=False,
                order_id=None,
                reason=f"error: {exc}",
                unresolved=[],
            )
    return out
