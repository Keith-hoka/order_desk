from order_desk.api.review_store import InMemoryReviewStore
from order_desk.review.priority import ReviewItem, ReviewStatus


def _item(item_id: str, org_id: str) -> ReviewItem:
    return ReviewItem(
        id=item_id,
        subject="s",
        body="b",
        extraction=None,
        field_flags=[],
        asks=[],
        violations=[],
        priority=1.0,
        org_id=org_id,
    )


def _store() -> InMemoryReviewStore:
    return InMemoryReviewStore(
        [_item("A-1", "org-a"), _item("A-2", "org-a"), _item("B-1", "org-b")]
    )


def test_list_filters_by_org() -> None:
    store = _store()
    a_items = store.list_items(org_id="org-a")
    assert {it.id for it in a_items} == {"A-1", "A-2"}
    b_items = store.list_items(org_id="org-b")
    assert {it.id for it in b_items} == {"B-1"}


def test_list_without_org_returns_all() -> None:
    # auth disabled / no org token -> no filtering (dev convenience)
    assert len(_store().list_items()) == 3


def test_get_cross_org_is_not_found() -> None:
    store = _store()
    assert store.get_item("B-1", org_id="org-a") is None  # 404, not 403
    assert store.get_item("B-1", org_id="org-b") is not None


def test_submit_cross_org_is_rejected() -> None:
    store = _store()
    assert store.submit_review("B-1", ReviewStatus.APPROVED, {}, org_id="org-a") is None
    # untouched
    assert store.get_item("B-1", org_id="org-b").status == ReviewStatus.PENDING


def test_submit_own_org_works() -> None:
    store = _store()
    item = store.submit_review("A-1", ReviewStatus.APPROVED, {}, org_id="org-a")
    assert item is not None
    assert item.status == ReviewStatus.APPROVED


def test_unknown_org_sees_empty_queue() -> None:
    # a freshly-registered org has no review items
    assert _store().list_items(org_id="org-new") == []


def test_edit_with_no_edits_downgrades_to_approved() -> None:
    """An "edited" submission that changed nothing must not become a correction.

    The flywheel reads every EDITED item as a reviewer's fix; an empty edit would
    teach the model that its own output was the correction.
    """
    store = _store()
    item = store.submit_review("A-1", ReviewStatus.EDITED, {}, org_id="org-a")
    assert item is not None
    assert item.status == ReviewStatus.APPROVED
    assert item.edits == {}


def test_edit_with_real_edits_stays_edited() -> None:
    store = _store()
    edits = {"customer_po_text": "PO-99999"}
    item = store.submit_review("A-1", ReviewStatus.EDITED, edits, org_id="org-a")
    assert item is not None
    assert item.status == ReviewStatus.EDITED
    assert item.edits == edits
