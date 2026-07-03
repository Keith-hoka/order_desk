import pytest

from order_desk.nonorder import generate_amendments
from order_desk.scenarios import generate_scenarios
from order_desk.schemas import ExtractedOrder, LineItem
from order_desk.scoring import (
    ClassificationTally,
    classification_metrics,
    empty_extraction,
    extraction_metrics,
    merge_tallies,
    norm_text,
    score_classification,
    score_extraction,
)


def item(product, quantity=None, unit=None, price=None, notes=None) -> LineItem:
    return LineItem(
        product_text=product,
        quantity=quantity,
        unit_text=unit,
        unit_price_text=price,
        item_notes=notes,
    )


def order(po=None, date=None, address=None, buyer=None, notes=None, items=()) -> ExtractedOrder:
    return ExtractedOrder(
        customer_po_text=po,
        requested_date_text=date,
        delivery_address_text=address,
        buyer_name_text=buyer,
        notes=notes,
        line_items=list(items),
    )


@pytest.fixture(scope="module")
def gold_corpus() -> list[ExtractedOrder]:
    scenarios = generate_scenarios(300, seed=20260707)
    amendments = generate_amendments(80, seed=20260707)
    return [s.gold_extraction() for s in scenarios] + [a.gold_extraction() for a in amendments]


def test_norm_preserves_punctuation() -> None:
    assert norm_text("  MPO/7686 ") == "mpo/7686"
    assert norm_text("Pallet   Wrap") == "pallet wrap"
    assert norm_text("MPO/7686") != norm_text("MPO7686")


def test_slot_outcomes_and_double_counting() -> None:
    gold = order(po="PO-1", address="Botany", buyer="Dana")
    pred = order(po="PO-2", date="ASAP", buyer="dana")
    metrics = extraction_metrics(score_extraction(gold, pred))
    fields = metrics["fields"]
    assert fields["customer_po_text"]["wrong"] == 1
    assert fields["customer_po_text"]["fp"] == 1
    assert fields["customer_po_text"]["fn"] == 1
    assert fields["requested_date_text"]["hallucination"] == 1
    assert fields["delivery_address_text"]["miss"] == 1
    assert fields["buyer_name_text"]["tp"] == 1
    assert fields["buyer_name_text"]["strict_rate"] == 0.0
    assert metrics["headline"]["tp"] == 1
    assert metrics["headline"]["fp"] == 2
    assert metrics["headline"]["fn"] == 2


def test_hand_computed_micro_f1() -> None:
    gold = order(
        po="PO-1",
        address="Botany",
        buyer="Dana",
        items=[
            item("clear tape", 6, "rolls", "$2.40"),
            item("pallet wrap", 12, "rolls", None, "urgent"),
        ],
    )
    pred = order(
        po="po-1",
        date="ASAP",
        buyer="Dana",
        items=[
            item("clear tape", 6, "rolls", "$2.40"),
            item("pallet  wrap", 10, "rolls"),
        ],
    )
    metrics = extraction_metrics(score_extraction(gold, pred))
    headline = metrics["headline"]
    assert (headline["tp"], headline["fp"], headline["fn"]) == (8, 2, 2)
    assert headline["precision"] == pytest.approx(0.8)
    assert headline["recall"] == pytest.approx(0.8)
    assert headline["f1"] == pytest.approx(0.8)
    assert headline["strict_rate"] == pytest.approx(0.75)
    assert headline["hallucination_rate"] == pytest.approx(0.5)
    assert metrics["fields"]["quantity"]["accuracy"] == pytest.approx(0.5)
    assert metrics["alignment"]["f1"] == pytest.approx(1.0)
    assert metrics["alignment"]["greedy_runs"] == 0
    assert metrics["notes"]["item_notes"]["token_fn"] == 1


def test_oracle_echo_is_perfect(gold_corpus) -> None:
    metrics = extraction_metrics(merge_tallies(score_extraction(g, g) for g in gold_corpus))
    assert metrics["headline"]["f1"] == pytest.approx(1.0)
    assert metrics["headline"]["fp"] == 0
    assert metrics["headline"]["fn"] == 0
    assert metrics["headline"]["strict_rate"] == pytest.approx(1.0)
    assert metrics["headline"]["hallucination_rate"] == 0.0
    assert metrics["alignment"]["f1"] == pytest.approx(1.0)
    assert metrics["validity"]["parse_rate"] == 1.0
    for row in metrics["fields"].values():
        assert row["fp"] == 0
        assert row["fn"] == 0


def test_empty_prediction_scores_zero(gold_corpus) -> None:
    metrics = extraction_metrics(
        merge_tallies(score_extraction(g, empty_extraction()) for g in gold_corpus)
    )
    assert metrics["headline"]["tp"] == 0
    assert metrics["headline"]["fp"] == 0
    assert metrics["headline"]["fn"] > 0
    assert metrics["headline"]["f1"] == 0.0
    assert metrics["alignment"]["f1"] == 0.0
    assert metrics["validity"]["parse_rate"] == 1.0


def test_parse_failure_scores_as_empty(gold_corpus) -> None:
    gold = gold_corpus[0]
    failed = score_extraction(gold, None)
    empty = score_extraction(gold, empty_extraction())
    assert failed.parsed == 0
    assert empty.parsed == 1
    failed.parsed = empty.parsed
    assert extraction_metrics(failed) == extraction_metrics(empty)


def test_alignment_is_order_invariant() -> None:
    gold = order(items=[item("alpha", 1, "rolls"), item("beta", 2, "packs"), item("gamma", 3)])
    pred_items = [item("gamma", 3), item("alpha", 1, "rolls"), item("beta", 2, "packs")]
    forward = extraction_metrics(score_extraction(gold, order(items=pred_items)))
    backward = extraction_metrics(score_extraction(gold, order(items=list(reversed(pred_items)))))
    assert forward == backward
    assert forward["alignment"]["f1"] == pytest.approx(1.0)


def test_zero_similarity_never_pairs() -> None:
    metrics = extraction_metrics(
        score_extraction(order(items=[item("alpha", 1)]), order(items=[item("beta", 2)]))
    )
    assert metrics["alignment"]["matched"] == 0
    assert metrics["alignment"]["f1"] == 0.0
    assert metrics["fields"]["product_text"]["miss"] == 1
    assert metrics["fields"]["product_text"]["hallucination"] == 1
    assert metrics["fields"]["quantity"]["miss"] == 1
    assert metrics["fields"]["quantity"]["hallucination"] == 1


def test_hallucinated_item_fields_are_fp() -> None:
    gold = order(items=[item("clear tape", 6, "rolls")])
    pred = order(items=[item("clear tape", 6, "rolls"), item("ghost widget", 5, "packs", "$1.00")])
    metrics = extraction_metrics(score_extraction(gold, pred))
    assert metrics["alignment"]["matched"] == 1
    assert metrics["headline"]["tp"] == 3
    assert metrics["headline"]["fp"] == 4
    assert metrics["headline"]["fn"] == 0


def test_greedy_fallback_is_counted_and_correct() -> None:
    items_gold = [item(f"product {i}", i + 1) for i in range(9)]
    pred_items = items_gold[4:] + items_gold[:4]
    tally = score_extraction(order(items=items_gold), order(items=pred_items))
    assert tally.alignment.greedy_runs == 1
    metrics = extraction_metrics(tally)
    assert metrics["alignment"]["f1"] == pytest.approx(1.0)
    assert metrics["headline"]["f1"] == pytest.approx(1.0)


def test_notes_token_f1_and_headline_isolation() -> None:
    gold = order(notes="call before delivery", items=[item("clear tape", 6)])
    with_notes = extraction_metrics(
        score_extraction(
            gold, order(notes="please call before 4pm delivery", items=[item("clear tape", 6)])
        )
    )
    row = with_notes["notes"]["notes"]
    assert (row["token_tp"], row["token_fp"], row["token_fn"]) == (3, 2, 0)
    assert row["token_f1"] == pytest.approx(0.75)
    without_notes = extraction_metrics(score_extraction(gold, order(items=[item("clear tape", 6)])))
    assert with_notes["headline"] == without_notes["headline"]


def test_classification_metrics_known_answer() -> None:
    pairs = (
        [("new_order", "new_order")] * 5
        + [("new_order", "inquiry")]
        + [("amendment", "new_order")]
        + [("cancellation", "cancellation")] * 2
        + [("inquiry", "other")]
        + [("other", "banana")]
        + [("amendment", "cancellation")]
    )
    tally = ClassificationTally()
    for gold, pred in pairs:
        tally.absorb(score_classification(gold, pred))
    metrics = classification_metrics(tally)
    assert metrics["records"] == 12
    assert metrics["accuracy"] == pytest.approx(7 / 12)
    assert metrics["order_missed"] == 2
    assert metrics["order_missed_rate"] == pytest.approx(0.25)
    assert metrics["invalid_predictions"] == 1
    assert metrics["per_class"]["new_order"]["precision"] == pytest.approx(5 / 6)
    assert metrics["per_class"]["new_order"]["recall"] == pytest.approx(5 / 6)
    assert metrics["per_class"]["amendment"]["recall"] == 0.0
    assert metrics["confusion"]["other->invalid"] == 1
