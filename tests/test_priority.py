from pathlib import Path

from order_desk.calibration import IsotonicCalibrator
from order_desk.pipeline.policy import PipelineState, RouteDecision
from order_desk.review.priority import (
    BAND_HI,
    BAND_LO,
    ReviewStatus,
    build_review_item,
    field_flags,
    priority_score,
    sort_queue,
)
from order_desk.schemas import ExtractedOrder

CAL = IsotonicCalibrator.load(Path("docs/phase4_calibrator.json"))

ORDER = ExtractedOrder(
    customer_po_text="PO-1",
    requested_date_text=None,
    delivery_address_text="Botany",
    buyer_name_text="Dana",
    notes=None,
    line_items=[
        {
            "product_text": "tape",
            "quantity": 6,
            "unit_text": "rolls",
            "unit_price_text": None,
            "item_notes": None,
        }
    ],
)


def test_band_membership() -> None:
    conf = {"a": 0.79, "b": 0.80, "c": 0.88, "d": 0.95, "e": 0.96, "f": 1.0}
    flags = {f.path: f for f in field_flags(conf, CAL)}
    assert not flags["a"].in_band  # below band
    assert flags["b"].in_band  # band edge lo
    assert flags["c"].in_band  # mid band
    assert flags["d"].in_band  # band edge hi
    assert not flags["e"].in_band  # above band
    assert not flags["f"].in_band  # perfect


def test_flags_carry_calibrated() -> None:
    flags = field_flags({"x": 0.88}, CAL)
    assert flags[0].raw_confidence == 0.88
    # calibrated is carried (in-sample, flat here) but present
    assert 0.0 <= flags[0].calibrated_confidence <= 1.0


def test_priority_orders_violation_over_ask_over_band() -> None:
    # violation dominates
    assert priority_score(band_count=0, n_asks=0, n_violations=1) > priority_score(
        band_count=0, n_asks=2, n_violations=0
    )
    # ask over band fields
    assert priority_score(band_count=0, n_asks=1, n_violations=0) > priority_score(
        band_count=3, n_asks=0, n_violations=0
    )


def test_build_review_item_computes_priority() -> None:
    # two band fields (0.88, 0.90), one ask, no violation
    state = PipelineState(
        subject="order",
        body="send tape. do you stock bubble wrap?",
        route=RouteDecision.EXTRACT,
        extraction=ORDER,
        confidence={
            "customer_po_text": 0.88,
            "delivery_address_text": 0.90,
            "line_items.0.product_text": 0.99,
        },
        asks=["blend ask"],
        violations=[],
    )
    item = build_review_item(state, CAL, "item-1")
    assert item.band_field_count == 2  # 0.88 and 0.90 in band
    assert item.priority == 4.0 * 1 + 1.0 * 2  # one ask + two band fields = 6.0
    assert item.status == ReviewStatus.PENDING
    assert item.extraction["customer_po_text"] == "PO-1"


def test_sort_queue_priority_desc() -> None:
    def mk(id_, conf, asks, viol):
        state = PipelineState(
            subject="s",
            body="b",
            route=RouteDecision.EXTRACT,
            extraction=ORDER,
            confidence=conf,
            asks=asks,
            violations=viol,
        )
        return build_review_item(state, CAL, id_)

    low = mk("low", {"a": 0.99}, [], [])  # priority 0
    mid = mk("mid", {"a": 0.88}, ["ask"], [])  # 4 + 1 = 5
    high = mk("high", {"a": 0.88}, ["ask"], ["viol"])  # 10 + 4 + 1 = 15
    queue = sort_queue([low, high, mid])
    assert [it.id for it in queue] == ["high", "mid", "low"]


def test_band_constants() -> None:
    assert BAND_LO == 0.80
    assert BAND_HI == 0.95
