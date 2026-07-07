"""Resolve mention-level product text to catalog SKUs (Phase 8).

The extraction is deliberately mention-level (Phase 1): the model emits the
product as written ("clear packing tape"), never a SKU it might hallucinate.
Turning a mention into a SKU is a downstream deterministic step, done here
against the catalog -- first an exact match on normalized aliases and names
(what humans actually write), then a fuzzy fallback with a conservative
threshold. Anything below threshold is left unresolved and flagged for manual
mapping rather than guessed, in keeping with surfacing boundaries as exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process

from order_desk.catalog import Catalog, Product, load_catalog, normalize

FUZZY_THRESHOLD = 80.0


@dataclass
class ProductMatch:
    query: str
    sku: str | None
    matched_name: str | None
    score: float
    resolved: bool
    method: str  # "alias_exact" | "name_exact" | "fuzzy" | "unresolved"


@dataclass
class ResolvedLine:
    product_text: str
    quantity: int | None
    unit_text: str | None
    match: ProductMatch


@dataclass
class ResolvedOrder:
    lines: list[ResolvedLine]

    @property
    def unresolved_count(self) -> int:
        return sum(1 for line in self.lines if not line.match.resolved)

    @property
    def all_resolved(self) -> bool:
        return self.unresolved_count == 0


def _exact_index(catalog: Catalog) -> dict[str, Product]:
    """Map normalized alias/name -> product for O(1) exact lookup."""
    index: dict[str, Product] = {}
    for product in catalog.products:
        index[normalize(product.name)] = product
        for alias in product.aliases:
            index[normalize(alias)] = product
    return index


def resolve_product(
    text: str, catalog: Catalog | None = None, threshold: float = FUZZY_THRESHOLD
) -> ProductMatch:
    catalog = catalog or load_catalog()
    norm = normalize(text)
    index = _exact_index(catalog)

    # layer 1: exact match on normalized alias or name
    hit = index.get(norm)
    if hit is not None:
        is_name = normalize(hit.name) == norm
        return ProductMatch(
            query=text,
            sku=hit.sku,
            matched_name=hit.name,
            score=100.0,
            resolved=True,
            method="name_exact" if is_name else "alias_exact",
        )

    # layer 2: fuzzy over the same normalized keys
    choices = list(index.keys())
    best = process.extractOne(norm, choices, scorer=fuzz.token_sort_ratio)
    if best is not None and best[1] >= threshold:
        product = index[best[0]]
        return ProductMatch(
            query=text,
            sku=product.sku,
            matched_name=product.name,
            score=float(best[1]),
            resolved=True,
            method="fuzzy",
        )

    return ProductMatch(
        query=text,
        sku=None,
        matched_name=None,
        score=float(best[1]) if best else 0.0,
        resolved=False,
        method="unresolved",
    )


def resolve_order(extraction, catalog: Catalog | None = None) -> ResolvedOrder:
    """Resolve every line item's product_text to a SKU."""
    catalog = catalog or load_catalog()
    lines = []
    for item in extraction.line_items:
        match = resolve_product(item.product_text, catalog)
        lines.append(
            ResolvedLine(
                product_text=item.product_text,
                quantity=item.quantity,
                unit_text=item.unit_text,
                match=match,
            )
        )
    return ResolvedOrder(lines=lines)
