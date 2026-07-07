"""ERP order format and sink (Phase 8).

A resolved order maps to an ERP-shaped structure: line items carry SKUs (not
mentions), catalog unit prices, and validated quantities; the header carries
PO, delivery address, and buyer. Because an order is atomic (decision B), an
order with any unresolved product is blocked entirely -- build_erp_order
returns None rather than submitting a partial order that would ship a customer
the wrong set of goods. The caller surfaces the block as a manual-mapping
notification instead.

OrderSink abstracts where a built order goes, mirroring EmailSource: a local
sink writes JSON and returns a receipt (the reproducible mock ERP), while a
real ERP (SAP/NetSuite/etc.) is left as an interface stub -- vendor-specific,
credentialed, and not reproducible here.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from order_desk.catalog import Catalog, load_catalog
from order_desk.fulfillment.resolve import ResolvedOrder


@dataclass
class ErpLine:
    sku: str
    product_name: str
    quantity: int
    unit: str
    unit_price_cents: int

    @property
    def line_total_cents(self) -> int:
        return self.quantity * self.unit_price_cents


@dataclass
class ErpOrder:
    customer_po: str | None
    delivery_address: str | None
    buyer_name: str | None
    lines: list[ErpLine]

    @property
    def total_cents(self) -> int:
        return sum(line.line_total_cents for line in self.lines)


@dataclass
class QuantityIssue:
    sku: str
    quantity: int
    kind: str  # "below_moq" | "above_max" | "missing"


@dataclass
class ErpBuildResult:
    order: ErpOrder | None
    unresolved: list[str]  # product_text of unresolved lines
    quantity_issues: list[QuantityIssue]

    @property
    def ok(self) -> bool:
        return self.order is not None and not self.unresolved and not self.quantity_issues


def build_erp_order(
    resolved: ResolvedOrder, extraction, catalog: Catalog | None = None
) -> ErpBuildResult:
    """Build an ERP order, or block it (order=None) if anything is off.

    Blocks (decision B) when any line is unresolved or any quantity violates
    the catalog's moq/max_qty, so a partial or invalid order never reaches the
    ERP.
    """
    catalog = catalog or load_catalog()
    by_sku = {p.sku: p for p in catalog.products}

    unresolved = [line.product_text for line in resolved.lines if not line.match.resolved]
    issues: list[QuantityIssue] = []
    lines: list[ErpLine] = []

    for line in resolved.lines:
        if not line.match.resolved:
            continue
        product = by_sku[line.match.sku]
        qty = line.quantity
        if qty is None:
            issues.append(QuantityIssue(sku=product.sku, quantity=0, kind="missing"))
            continue
        if qty < product.moq:
            issues.append(QuantityIssue(sku=product.sku, quantity=qty, kind="below_moq"))
        elif qty > product.max_qty:
            issues.append(QuantityIssue(sku=product.sku, quantity=qty, kind="above_max"))
        lines.append(
            ErpLine(
                sku=product.sku,
                product_name=product.name,
                quantity=qty,
                unit=product.unit,
                unit_price_cents=product.unit_price_cents,
            )
        )

    if unresolved or issues:
        return ErpBuildResult(order=None, unresolved=unresolved, quantity_issues=issues)

    order = ErpOrder(
        customer_po=extraction.customer_po_text,
        delivery_address=extraction.delivery_address_text,
        buyer_name=extraction.buyer_name_text,
        lines=lines,
    )
    return ErpBuildResult(order=order, unresolved=[], quantity_issues=[])


@dataclass
class OrderReceipt:
    order_id: str
    status: str
    submitted_at: str
    total_cents: int


class OrderSink(Protocol):
    def submit(self, order: ErpOrder) -> OrderReceipt:
        """Submit an ERP order, returning a receipt with an order id."""
        ...


class LocalOrderSink:
    """Reproducible mock ERP: appends orders to a JSON file, returns a receipt."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def submit(self, order: ErpOrder) -> OrderReceipt:
        records = self._load()
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        receipt = OrderReceipt(
            order_id=order_id,
            status="accepted",
            submitted_at=datetime.now(UTC).isoformat(),
            total_cents=order.total_cents,
        )
        records.append({"receipt": asdict(receipt), "order": asdict(order)})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return receipt


class ErpOrderSink:
    """Real ERP sink -- interface stub, not implemented.

    A production implementation would map ErpOrder to the target ERP's order
    schema and POST it over that ERP's API (SAP OData, NetSuite SuiteTalk,
    Odoo JSON-RPC, etc.), authenticating with credentials from the environment,
    and translate the ERP's response into an OrderReceipt. It is deliberately
    unimplemented: the integration is vendor-specific and needs credentials and
    a live ERP that cannot be reproduced here. The build/submit contract is
    identical whatever the sink.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self._api_key = api_key

    def submit(self, order: ErpOrder) -> OrderReceipt:
        raise NotImplementedError(
            "ErpOrderSink is an interface stub; implement ERP submission for a live system"
        )
