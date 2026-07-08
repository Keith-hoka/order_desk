from order_desk.flywheel.blended import (
    case_to_record,
    generate_blended_cases,
)


def test_generates_requested_count() -> None:
    cases = generate_blended_cases(n=50, seed=1)
    assert len(cases) == 50


def test_deterministic_by_seed() -> None:
    a = generate_blended_cases(n=20, seed=42)
    b = generate_blended_cases(n=20, seed=42)
    assert [c.body for c in a] == [c.body for c in b]
    # different seed -> different
    c = generate_blended_cases(n=20, seed=99)
    assert [x.body for x in a] != [x.body for x in c]


def test_inquiry_product_not_in_gold() -> None:
    # for non-counter cases, the inquired product must not be a gold line item
    cases = generate_blended_cases(n=100, seed=7)
    non_counter = [c for c in cases if not c.is_counter_example]
    assert len(non_counter) > 0
    for case in non_counter:
        gold_products = {li["product_text"] for li in case.gold_extraction["line_items"]}
        # non-counter cases have exactly one ordered product (the inquiry is excluded)
        assert len(gold_products) == 1


def test_counter_example_product_in_gold() -> None:
    # counter-examples order the second product too -> two gold line items
    cases = generate_blended_cases(n=100, seed=7)
    counters = [c for c in cases if c.is_counter_example]
    assert len(counters) > 0
    for case in counters:
        assert len(case.gold_extraction["line_items"]) == 2  # both ordered


def test_counter_fraction_roughly_honoured() -> None:
    cases = generate_blended_cases(n=200, seed=3, counter_fraction=0.22)
    counters = sum(1 for c in cases if c.is_counter_example)
    # within a reasonable band of 22%
    assert 0.12 < counters / len(cases) < 0.32


def test_case_to_record_shape() -> None:
    case = generate_blended_cases(n=1, seed=1)[0]
    rec = case_to_record(case)
    assert rec["email_class"] == "new_order"
    assert "gold_extraction" in rec
    assert "line_items" in rec["gold_extraction"]
    assert rec["subject"] == case.subject


def test_gold_has_full_order_fields() -> None:
    case = generate_blended_cases(n=1, seed=5)[0]
    gold = case.gold_extraction
    # full order shape, not just line items
    for key in (
        "customer_po_text",
        "delivery_address_text",
        "buyer_name_text",
        "requested_date_text",
        "notes",
        "line_items",
    ):
        assert key in gold
