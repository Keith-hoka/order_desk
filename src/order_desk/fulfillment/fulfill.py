"""Fulfillment service: resolve, submit to ERP, notify (Phase 8).

Ties the three pieces together for an approved order: resolve product mentions
to SKUs, build the ERP order (blocking on unresolved or invalid quantities per
decision B), submit it to the sink if clean, and notify either way. This is the
last leg of the workflow -- from "a reviewer approved it" to "it is in the ERP
and the right people know," or "it is held for manual mapping."
"""

from __future__ import annotations

from dataclasses import dataclass, field

from order_desk.catalog import Catalog, load_catalog
from order_desk.fulfillment.erp import OrderSink, build_erp_order
from order_desk.fulfillment.notify import (
    Notification,
    Notifier,
    NotifyEvent,
    needs_mapping_message,
    order_submitted_message,
)
from order_desk.fulfillment.resolve import resolve_order
from order_desk.schemas import ExtractedOrder


@dataclass
class FulfillResult:
    submitted: bool
    order_id: str | None
    reason: str  # "submitted" | "held_for_mapping"
    unresolved: list[str] = field(default_factory=list)


def fulfill_order(
    extraction_dict: dict,
    sink: OrderSink,
    notifier: Notifier,
    catalog: Catalog | None = None,
) -> FulfillResult:
    """Resolve, build, submit-or-hold, and notify for one approved order."""
    catalog = catalog or load_catalog()
    extraction = ExtractedOrder.model_validate(extraction_dict)
    resolved = resolve_order(extraction, catalog)
    result = build_erp_order(resolved, extraction, catalog)

    if result.ok and result.order is not None:
        receipt = sink.submit(result.order)
        notifier.send(
            Notification(
                event=NotifyEvent.ORDER_SUBMITTED,
                text=order_submitted_message(
                    po=result.order.customer_po,
                    order_id=receipt.order_id,
                    n_lines=len(result.order.lines),
                    total_cents=result.order.total_cents,
                ),
            )
        )
        return FulfillResult(submitted=True, order_id=receipt.order_id, reason="submitted")

    issue_strs = [f"{i.sku} {i.kind}" for i in result.quantity_issues]
    notifier.send(
        Notification(
            event=NotifyEvent.NEEDS_MAPPING,
            text=needs_mapping_message(
                po=extraction.customer_po_text,
                unresolved=result.unresolved,
                issues=issue_strs,
            ),
        )
    )
    return FulfillResult(
        submitted=False,
        order_id=None,
        reason="held_for_mapping",
        unresolved=result.unresolved,
    )
