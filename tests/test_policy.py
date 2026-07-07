from order_desk.pipeline.policy import (
    PipelineState,
    RouteDecision,
    detect_product_inquiry,
    policy_violations,
    route_for_class,
)
from order_desk.schemas import EmailClass, ExtractedOrder

EMPTY = ExtractedOrder(
    customer_po_text=None,
    requested_date_text=None,
    delivery_address_text=None,
    buyer_name_text=None,
    notes=None,
    line_items=[],
)


def test_route_mapping_is_total_and_correct() -> None:
    assert route_for_class(EmailClass.NEW_ORDER) == RouteDecision.EXTRACT
    assert route_for_class(EmailClass.AMENDMENT) == RouteDecision.EXTRACT
    assert route_for_class(EmailClass.CANCELLATION) == RouteDecision.CANCEL
    assert route_for_class(EmailClass.INQUIRY) == RouteDecision.INQUIRY
    assert route_for_class(EmailClass.OTHER) == RouteDecision.DISCARD
    # total: every class maps
    for cls in EmailClass:
        assert isinstance(route_for_class(cls), RouteDecision)


def test_product_inquiry_heuristic_targets_product_questions() -> None:
    assert detect_product_inquiry("Do you stock 20mm bubble wrap?")
    assert detect_product_inquiry("do you have poly mailers in stock")
    assert detect_product_inquiry("Is there a bulk price for cartons?")
    assert detect_product_inquiry("What's the lead time on pallets?")
    # polite / non-product questions should NOT trip it
    assert not detect_product_inquiry("Could you confirm receipt?")
    assert not detect_product_inquiry("Is that ok with you?")
    assert not detect_product_inquiry("Please send 12 rolls of tape.")


def test_policy_violations_flag_route_extraction_mismatch() -> None:
    # EXTRACT without extraction
    s1 = PipelineState(subject="s", body="b", route=RouteDecision.EXTRACT)
    assert "EXTRACT route without an extraction" in policy_violations(s1)
    # EXTRACT with extraction: clean
    s2 = PipelineState(subject="s", body="b", route=RouteDecision.EXTRACT, extraction=EMPTY)
    assert policy_violations(s2) == []
    # INQUIRY carrying an extraction: violation
    s3 = PipelineState(subject="s", body="b", route=RouteDecision.INQUIRY, extraction=EMPTY)
    assert any("unexpected extraction" in msg for msg in policy_violations(s3))
    # no route: violation
    s4 = PipelineState(subject="s", body="b")
    assert "no route assigned" in policy_violations(s4)


def test_pipeline_state_forbids_extra_fields() -> None:
    import pydantic
    import pytest

    with pytest.raises(pydantic.ValidationError):
        PipelineState(subject="s", body="b", bogus_field=1)
