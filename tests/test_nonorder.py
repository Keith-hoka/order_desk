import pytest

from order_desk.catalog import load_catalog
from order_desk.customers import load_customers
from order_desk.nonorder import (
    AmendmentChange,
    ContractViolation,
    InquiryType,
    OtherType,
    generate_amendments,
    generate_cancellations,
    generate_inquiries,
    generate_others,
    render_amendment,
    render_cancellation,
    render_inquiry,
    render_other,
    verify_amendment,
    verify_cancellation,
    verify_inquiry,
    verify_other,
)
from order_desk.renderer import _term_pattern
from order_desk.schemas import ExtractedOrder

SEED = 20260704
RENDER_SEED = 77


@pytest.fixture(scope="module")
def amendments():
    return generate_amendments(300, seed=SEED)


@pytest.fixture(scope="module")
def cancellations():
    return generate_cancellations(200, seed=SEED)


@pytest.fixture(scope="module")
def inquiries():
    return generate_inquiries(200, seed=SEED)


@pytest.fixture(scope="module")
def others():
    return generate_others(200, seed=SEED)


def test_amendment_invariants_and_coverage(amendments) -> None:
    book = load_customers()
    assert {a.change_type for a in amendments} == set(AmendmentChange)
    assert any(a.buyer_signature is None for a in amendments)
    assert any(a.buyer_signature is not None for a in amendments)
    for index, amendment in enumerate(amendments):
        assert amendment.scenario_id == f"AMD-{index:06d}"
        customer = book.resolve_customer(amendment.sender_email)
        assert customer is not None
        assert customer.customer_id == amendment.customer_id
        assert (customer.po_template is None) == (amendment.referenced_po is None)
        ExtractedOrder.model_validate(amendment.gold_extraction().model_dump())


def test_amendment_gold_matches_change_type(amendments) -> None:
    for amendment in amendments:
        gold = amendment.gold_extraction()
        assert gold.customer_po_text == amendment.referenced_po
        assert gold.buyer_name_text == amendment.buyer_signature
        if amendment.change_type is AmendmentChange.DATE_CHANGE:
            assert gold.line_items == []
            assert gold.requested_date_text == amendment.date_phrase is not None
        else:
            assert gold.requested_date_text is None
            assert len(gold.line_items) == 1
            item = gold.line_items[0]
            assert item.product_text == amendment.line.product_surface
            if amendment.change_type is AmendmentChange.REMOVE_ITEM:
                assert item.quantity is None and item.unit_text is None
            else:
                assert item.quantity == amendment.line.quantity_value >= 1


def test_amendment_contracts_hold(amendments) -> None:
    for amendment in amendments:
        verify_amendment(amendment, render_amendment(amendment, RENDER_SEED))


def test_amendment_verifier_catches_tampering(amendments) -> None:
    scenario = next(a for a in amendments if a.line is not None)
    email = render_amendment(scenario, RENDER_SEED)
    verify_amendment(scenario, email)

    swapped = email.body.replace(scenario.line.product_surface, "the thing")
    with pytest.raises(ContractViolation, match="missing"):
        verify_amendment(scenario, email.model_copy(update={"body": swapped}))

    with pytest.raises(ContractViolation, match="digit-closure"):
        verify_amendment(
            scenario, email.model_copy(update={"body": email.body + "\nNeed them by 4pm.\n"})
        )

    with pytest.raises(ContractViolation, match="term-closure"):
        verify_amendment(
            scenario,
            email.model_copy(update={"body": email.body + "\nPlease pack them tight.\n"}),
        )


def test_cancellation_invariants_and_contracts(cancellations) -> None:
    book = load_customers()
    assert any(c.referenced_po is not None for c in cancellations)
    assert any(c.referenced_po is None for c in cancellations)
    for cancellation in cancellations:
        customer = book.resolve_customer(cancellation.sender_email)
        assert customer is not None
        if customer.po_template is None:
            assert cancellation.referenced_po is None
        verify_cancellation(cancellation, render_cancellation(cancellation, RENDER_SEED))


def test_inquiry_types_markers_and_lookalike(inquiries) -> None:
    assert {i.inquiry_type for i in inquiries} == set(InquiryType)
    lookalike_seen = False
    pattern = _term_pattern()
    for inquiry in inquiries:
        rendered = render_inquiry(inquiry, RENDER_SEED)
        verify_inquiry(inquiry, rendered)
        if (
            inquiry.inquiry_type is InquiryType.QUOTE_REQUEST
            and any(ch.isdigit() for ch in rendered.body)
            and pattern.search(rendered.body)
        ):
            lookalike_seen = True
    assert lookalike_seen


def test_other_contracts_and_sender_rules(others) -> None:
    book = load_customers()
    assert {o.other_type for o in others} == set(OtherType)
    for other in others:
        verify_other(other, render_other(other, RENDER_SEED))
        resolved = book.resolve_customer(other.sender_email)
        if other.other_type is OtherType.MISDIRECTED:
            assert resolved is not None
            assert other.customer_id == resolved.customer_id
        else:
            assert resolved is None
            assert other.customer_id is None


def test_other_verifier_rejects_po_pattern(others) -> None:
    scenario = others[0]
    rendered = render_other(scenario, RENDER_SEED)
    verify_other(scenario, rendered)
    broken = rendered.model_copy(update={"body": rendered.body + "\nPO-12345\n"})
    with pytest.raises(ContractViolation, match="PO pattern"):
        verify_other(scenario, broken)


def test_nonorder_renderers_are_pure_and_deterministic(
    amendments, cancellations, inquiries, others
) -> None:
    catalog = load_catalog()
    assert catalog is not None  # loaded fixtures stay immutable through rendering
    for batch, renderer in (
        (amendments[:50], render_amendment),
        (cancellations[:50], render_cancellation),
        (inquiries[:50], render_inquiry),
        (others[:50], render_other),
    ):
        before = [scenario.model_dump_json() for scenario in batch]
        first = [renderer(scenario, RENDER_SEED).model_dump() for scenario in batch]
        second = [renderer(scenario, RENDER_SEED).model_dump() for scenario in batch]
        assert first == second
        assert [scenario.model_dump_json() for scenario in batch] == before
        shifted = [renderer(scenario, RENDER_SEED + 1).model_dump() for scenario in batch]
        differing = sum(a != b for a, b in zip(first, shifted, strict=True))
        assert differing >= int(0.4 * len(batch))
