"""Exception-queue store (Phase 7).

A ReviewStore serves the sorted exception queue and records reviewer
decisions. JsonReviewStore reads a pre-computed queue (built offline in 7.3
from the human .eml corpus run through the pipeline) and persists reviews to a
JSON file. Tests inject an in-memory store. Keeping the queue pre-computed
avoids running the real pipeline (OpenAI + Modal) on every request -- review
is triage over already-processed emails.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from order_desk.api.tenancy import DEMO_ORG_ID
from order_desk.review.priority import ReviewItem, ReviewStatus, sort_queue


def item_to_dict(item: ReviewItem) -> dict:
    d = asdict(item)
    d["status"] = item.status.value
    return d


def item_from_dict(d: dict) -> ReviewItem:
    from order_desk.review.priority import FieldFlag

    return ReviewItem(
        id=d["id"],
        subject=d["subject"],
        body=d["body"],
        extraction=d["extraction"],
        field_flags=[FieldFlag(**f) for f in d["field_flags"]],
        asks=d["asks"],
        violations=d["violations"],
        priority=d["priority"],
        status=ReviewStatus(d["status"]),
        edits=d.get("edits", {}),
        org_id=d.get("org_id", DEMO_ORG_ID),
        fulfillment=d.get("fulfillment"),
    )


class ReviewStore(Protocol):
    def list_items(self, org_id: str | None = None) -> list[ReviewItem]: ...
    def get_item(self, item_id: str, org_id: str | None = None) -> ReviewItem | None: ...
    def submit_review(
        self,
        item_id: str,
        action: ReviewStatus,
        edits: dict[str, str],
        org_id: str | None = None,
    ) -> ReviewItem | None: ...
    def record_fulfillment(self, item_id: str, fulfillment: dict) -> None: ...
    def add_item(self, item: ReviewItem) -> None: ...
    def delete_item(self, item_id: str) -> None: ...


def _effective_status(action: ReviewStatus, edits: dict[str, str]) -> ReviewStatus:
    """An "edited" submission that changed nothing is an approval.

    The flywheel treats every EDITED item as a correction signal, so recording an
    edit that carries no edits would teach the model that its own output was a
    reviewer's fix. Downgrade rather than lie.
    """
    if action == ReviewStatus.EDITED and not edits:
        return ReviewStatus.APPROVED
    return action


def _record_review(item: ReviewItem, action: ReviewStatus, edits: dict[str, str]) -> None:
    """Approving an already-edited item confirms the corrected version.

    The status becomes approved -- the reviewer's decision -- but the edits
    stay: replacing them with {} would revert the UI to the model's output,
    drop the flywheel's correction signal (which keys on edits, not status),
    and fulfil with the uncorrected extraction. A rejection still clears them:
    it says "not an order", not "keep my fix".
    """
    if action == ReviewStatus.APPROVED and not edits and item.edits:
        item.status = ReviewStatus.APPROVED
        return
    item.status = _effective_status(action, edits)
    item.edits = dict(edits)


def _migrate_fulfillment(item: ReviewItem) -> ReviewItem:
    """Stamp legacy fulfilment records (pre-for_edits) at load time.

    Such a record was fulfilled with whatever the item's edits were when it was
    written, so it covers the edits as loaded -- and only those. Stamping once
    here (rather than treating it as always-current at comparison time) lets
    later corrections re-open fulfilment instead of being frozen out forever.
    """
    if item.fulfillment is not None and "for_edits" not in item.fulfillment:
        item.fulfillment["for_edits"] = dict(item.edits)
        item.fulfillment.setdefault("amends", None)
    return item


def _visible(item: ReviewItem | None, org_id: str | None) -> ReviewItem | None:
    """An item from another org is indistinguishable from a missing one.

    Returning 404 rather than 403 on a cross-tenant id keeps the existence of
    other tenants' items from leaking through id enumeration.
    """
    if item is None:
        return None
    if org_id is not None and item.org_id != org_id:
        return None
    return item


class InMemoryReviewStore:
    def __init__(self, items: list[ReviewItem]) -> None:
        self._items = {it.id: _migrate_fulfillment(it) for it in items}

    def list_items(self, org_id: str | None = None) -> list[ReviewItem]:
        items = list(self._items.values())
        if org_id is not None:
            items = [it for it in items if it.org_id == org_id]
        return sort_queue(items)

    def get_item(self, item_id: str, org_id: str | None = None) -> ReviewItem | None:
        return _visible(self._items.get(item_id), org_id)

    def submit_review(
        self,
        item_id: str,
        action: ReviewStatus,
        edits: dict[str, str],
        org_id: str | None = None,
    ) -> ReviewItem | None:
        item = _visible(self._items.get(item_id), org_id)
        if item is None:
            return None
        _record_review(item, action, edits)
        return item

    def record_fulfillment(self, item_id: str, fulfillment: dict) -> None:
        self._items[item_id].fulfillment = fulfillment

    def add_item(self, item: ReviewItem) -> None:
        self._items[item.id] = item

    def delete_item(self, item_id: str) -> None:
        self._items.pop(item_id, None)


class JsonReviewStore:
    """Reads the queue JSON, persists reviews back to the same file."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._items = {d["id"]: _migrate_fulfillment(item_from_dict(d)) for d in data}

    def _persist(self) -> None:
        data = [item_to_dict(it) for it in self._items.values()]
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_items(self, org_id: str | None = None) -> list[ReviewItem]:
        items = list(self._items.values())
        if org_id is not None:
            items = [it for it in items if it.org_id == org_id]
        return sort_queue(items)

    def get_item(self, item_id: str, org_id: str | None = None) -> ReviewItem | None:
        return _visible(self._items.get(item_id), org_id)

    def submit_review(
        self,
        item_id: str,
        action: ReviewStatus,
        edits: dict[str, str],
        org_id: str | None = None,
    ) -> ReviewItem | None:
        item = _visible(self._items.get(item_id), org_id)
        if item is None:
            return None
        _record_review(item, action, edits)
        self._persist()
        return item

    def record_fulfillment(self, item_id: str, fulfillment: dict) -> None:
        self._items[item_id].fulfillment = fulfillment
        self._persist()

    def add_item(self, item: ReviewItem) -> None:
        self._items[item.id] = item
        self._persist()

    def delete_item(self, item_id: str) -> None:
        self._items.pop(item_id, None)
        self._persist()
