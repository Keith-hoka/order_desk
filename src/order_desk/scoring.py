"""Extraction and classification scoring core (step 1.9a).

Semantics locked in step 1.9 and pinned by known-answer tests:

- Equivalence: strings compare under casefold + whitespace collapse with
  punctuation intact ("MPO/7686" != "MPO7686"); quantities compare as ints.
  Byte-exact agreement rides along as the strict-verbatim rate -- a
  diagnostic, never the headline.
- Slot accounting: every gold/pred slot lands in exactly one outcome --
  correct, wrong, hallucination (gold null, pred non-null), miss (gold
  non-null, pred null), null_agree. fp = wrong + hallucination,
  fn = wrong + miss, so a wrong value costs both and null/null agreement
  stays out of F1. Per-field accuracy = (correct + null_agree) / slots.
  Hallucination rate = hallucination / (hallucination + null_agree), i.e.
  P(pred non-null | gold null).
- Headline micro-F1 spans eight strict fields (po / date / address / buyer;
  product / quantity / unit / price). notes and item_notes score separately
  at token level (casefold token multisets).
- Line items align before scoring: similarity 3*[product] + [qty] + [unit] +
  [price] over non-null equal values; optimal assignment when both sides
  have <= 8 items (exhaustive), greedy beyond (counted; never expected on
  this corpus); zero-similarity pairs never form. Unmatched gold fields
  score as misses, unmatched pred fields as hallucinations. Alignment F1:
  tp = matched pairs with equivalent product_text, precision over pred
  items, recall over gold items. With these weights a full qty+unit+price
  coincidence (3) can tie a product-only match (3); ties break
  deterministically by enumeration order.
- A strict-parse failure (pred is None) scores as the empty extraction and
  is never excluded; validity and repair usage ride in the tally.
- Classification: accuracy, per-class P/R/F1, macro-F1 over the five real
  classes, confusion counts; an out-of-enum label becomes "invalid"
  (prediction-side bucket only). Order-missed operationalizes SPEC "true
  order classified as non-order": gold in {new_order, amendment} predicted
  in {cancellation, inquiry, other, invalid}. new_order/amendment confusion
  is not a miss -- both enter the extraction path.

EVAL_VERSION stamps every metrics dict; any change to the semantics above
bumps it (same discipline as the schema snapshot and the corpus freezes).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from itertools import permutations
from typing import Any

from order_desk.schemas import EmailClass, ExtractedOrder, LineItem

EVAL_VERSION = 2

ORDER_FIELDS = (
    "customer_po_text",
    "requested_date_text",
    "delivery_address_text",
    "buyer_name_text",
)
ITEM_FIELDS = ("product_text", "quantity", "unit_text", "unit_price_text")
HEADLINE_FIELDS = ORDER_FIELDS + ITEM_FIELDS
NOTES_FIELDS = ("notes", "item_notes")
MAX_EXHAUSTIVE_ITEMS = 8
ORDER_BEARING = frozenset({"new_order", "amendment"})
NON_ORDER_PRED = frozenset({"cancellation", "inquiry", "other", "invalid"})


def norm_text(text: str) -> str:
    """Casefold and collapse whitespace; punctuation is preserved."""
    return " ".join(text.split()).casefold()


def _equivalent(gold: str | int, pred: str | int) -> bool:
    if isinstance(gold, str) and isinstance(pred, str):
        return norm_text(gold) == norm_text(pred)
    return gold == pred


@dataclass
class SlotCounts:
    correct: int = 0
    strict_correct: int = 0
    wrong: int = 0
    hallucination: int = 0
    miss: int = 0
    null_agree: int = 0

    @property
    def tp(self) -> int:
        return self.correct

    @property
    def fp(self) -> int:
        return self.wrong + self.hallucination

    @property
    def fn(self) -> int:
        return self.wrong + self.miss

    @property
    def slots(self) -> int:
        return self.correct + self.wrong + self.hallucination + self.miss + self.null_agree

    def absorb(self, other: SlotCounts) -> None:
        self.correct += other.correct
        self.strict_correct += other.strict_correct
        self.wrong += other.wrong
        self.hallucination += other.hallucination
        self.miss += other.miss
        self.null_agree += other.null_agree


@dataclass
class TokenCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    null_agree: int = 0

    def absorb(self, other: TokenCounts) -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn
        self.null_agree += other.null_agree


@dataclass
class AlignmentCounts:
    gold_items: int = 0
    pred_items: int = 0
    matched: int = 0
    product_correct: int = 0
    greedy_runs: int = 0

    def absorb(self, other: AlignmentCounts) -> None:
        self.gold_items += other.gold_items
        self.pred_items += other.pred_items
        self.matched += other.matched
        self.product_correct += other.product_correct
        self.greedy_runs += other.greedy_runs


def _new_fields() -> dict[str, SlotCounts]:
    return {name: SlotCounts() for name in HEADLINE_FIELDS}


def _new_notes() -> dict[str, TokenCounts]:
    return {name: TokenCounts() for name in NOTES_FIELDS}


@dataclass
class ExtractionTally:
    records: int = 0
    parsed: int = 0
    repair_used: int = 0
    fields: dict[str, SlotCounts] = field(default_factory=_new_fields)
    notes: dict[str, TokenCounts] = field(default_factory=_new_notes)
    alignment: AlignmentCounts = field(default_factory=AlignmentCounts)

    def absorb(self, other: ExtractionTally) -> None:
        self.records += other.records
        self.parsed += other.parsed
        self.repair_used += other.repair_used
        for name, counts in other.fields.items():
            self.fields[name].absorb(counts)
        for name, counts in other.notes.items():
            self.notes[name].absorb(counts)
        self.alignment.absorb(other.alignment)


def merge_tallies(tallies: Iterable[ExtractionTally]) -> ExtractionTally:
    total = ExtractionTally()
    for tally in tallies:
        total.absorb(tally)
    return total


def empty_extraction() -> ExtractedOrder:
    """The canonical empty prediction; strict-parse failures score as this."""
    return ExtractedOrder(
        customer_po_text=None,
        requested_date_text=None,
        delivery_address_text=None,
        buyer_name_text=None,
        notes=None,
        line_items=[],
    )


def _score_slot(counts: SlotCounts, gold: str | int | None, pred: str | int | None) -> None:
    if gold is None and pred is None:
        counts.null_agree += 1
    elif gold is None:
        counts.hallucination += 1
    elif pred is None:
        counts.miss += 1
    elif _equivalent(gold, pred):
        counts.correct += 1
        if gold == pred:
            counts.strict_correct += 1
    else:
        counts.wrong += 1


def _score_tokens(counts: TokenCounts, gold: str | None, pred: str | None) -> None:
    if gold is None and pred is None:
        counts.null_agree += 1
        return
    gold_tokens = Counter(gold.casefold().split()) if gold is not None else Counter()
    pred_tokens = Counter(pred.casefold().split()) if pred is not None else Counter()
    overlap = sum((gold_tokens & pred_tokens).values())
    counts.tp += overlap
    counts.fp += sum(pred_tokens.values()) - overlap
    counts.fn += sum(gold_tokens.values()) - overlap


def _similarity(gold: LineItem, pred: LineItem) -> int:
    score = 0
    if _equivalent(gold.product_text, pred.product_text):
        score += 3
    if gold.quantity is not None and pred.quantity is not None and gold.quantity == pred.quantity:
        score += 1
    for name in ("unit_text", "unit_price_text"):
        gold_value, pred_value = getattr(gold, name), getattr(pred, name)
        if (
            gold_value is not None
            and pred_value is not None
            and _equivalent(gold_value, pred_value)
        ):
            score += 1
    return score


def _align_items(
    gold_items: Sequence[LineItem], pred_items: Sequence[LineItem]
) -> tuple[list[tuple[int, int]], bool]:
    """Pair items maximizing summed similarity; zero-similarity never pairs."""
    if not gold_items or not pred_items:
        return [], False
    sims = [[_similarity(g, p) for p in pred_items] for g in gold_items]
    n_gold, n_pred = len(gold_items), len(pred_items)
    if n_gold <= MAX_EXHAUSTIVE_ITEMS and n_pred <= MAX_EXHAUSTIVE_ITEMS:
        best_total, best_pairs = -1, []
        if n_gold <= n_pred:
            for combo in permutations(range(n_pred), n_gold):
                total = sum(sims[i][j] for i, j in enumerate(combo))
                if total > best_total:
                    best_total, best_pairs = total, list(enumerate(combo))
        else:
            for combo in permutations(range(n_gold), n_pred):
                total = sum(sims[i][j] for j, i in enumerate(combo))
                if total > best_total:
                    best_total, best_pairs = total, [(i, j) for j, i in enumerate(combo)]
        return [(i, j) for i, j in best_pairs if sims[i][j] > 0], False
    ranked = sorted(
        ((sims[i][j], i, j) for i in range(n_gold) for j in range(n_pred) if sims[i][j] > 0),
        key=lambda entry: (-entry[0], entry[1], entry[2]),
    )
    used_gold: set[int] = set()
    used_pred: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for _, i, j in ranked:
        if i in used_gold or j in used_pred:
            continue
        pairs.append((i, j))
        used_gold.add(i)
        used_pred.add(j)
    return pairs, True


def score_extraction(
    gold: ExtractedOrder, pred: ExtractedOrder | None, *, repair_used: bool = False
) -> ExtractionTally:
    tally = ExtractionTally(records=1)
    if pred is None:
        pred = empty_extraction()
    else:
        tally.parsed = 1
    if repair_used:
        tally.repair_used = 1

    for name in ORDER_FIELDS:
        _score_slot(tally.fields[name], getattr(gold, name), getattr(pred, name))
    _score_tokens(tally.notes["notes"], gold.notes, pred.notes)

    pairs, greedy = _align_items(gold.line_items, pred.line_items)
    tally.alignment.gold_items = len(gold.line_items)
    tally.alignment.pred_items = len(pred.line_items)
    tally.alignment.matched = len(pairs)
    tally.alignment.greedy_runs = 1 if greedy else 0

    matched_gold = {i for i, _ in pairs}
    matched_pred = {j for _, j in pairs}
    for i, j in pairs:
        gold_item, pred_item = gold.line_items[i], pred.line_items[j]
        if _equivalent(gold_item.product_text, pred_item.product_text):
            tally.alignment.product_correct += 1
        for name in ITEM_FIELDS:
            _score_slot(tally.fields[name], getattr(gold_item, name), getattr(pred_item, name))
        _score_tokens(tally.notes["item_notes"], gold_item.item_notes, pred_item.item_notes)
    for i, gold_item in enumerate(gold.line_items):
        if i in matched_gold:
            continue
        for name in ITEM_FIELDS:
            if getattr(gold_item, name) is not None:
                tally.fields[name].miss += 1
        if gold_item.item_notes is not None:
            _score_tokens(tally.notes["item_notes"], gold_item.item_notes, None)
    for j, pred_item in enumerate(pred.line_items):
        if j in matched_pred:
            continue
        for name in ITEM_FIELDS:
            if getattr(pred_item, name) is not None:
                tally.fields[name].hallucination += 1
        if pred_item.item_notes is not None:
            _score_tokens(tally.notes["item_notes"], None, pred_item.item_notes)
    return tally


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    denominator = precision + recall
    f1 = 2 * precision * recall / denominator if denominator else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def extraction_metrics(tally: ExtractionTally) -> dict[str, Any]:
    headline = SlotCounts()
    for name in HEADLINE_FIELDS:
        headline.absorb(tally.fields[name])
    fields_report: dict[str, Any] = {}
    for name in HEADLINE_FIELDS:
        counts = tally.fields[name]
        fields_report[name] = {
            "tp": counts.tp,
            "fp": counts.fp,
            "fn": counts.fn,
            "wrong": counts.wrong,
            "hallucination": counts.hallucination,
            "miss": counts.miss,
            "null_agree": counts.null_agree,
            **_prf(counts.tp, counts.fp, counts.fn),
            "accuracy": _ratio(counts.correct + counts.null_agree, counts.slots),
            "strict_rate": _ratio(counts.strict_correct, counts.correct),
            "hallucination_rate": _ratio(
                counts.hallucination, counts.hallucination + counts.null_agree
            ),
        }
    notes_report = {
        name: {
            "token_tp": counts.tp,
            "token_fp": counts.fp,
            "token_fn": counts.fn,
            "null_agree": counts.null_agree,
            **{
                f"token_{key}": value
                for key, value in _prf(counts.tp, counts.fp, counts.fn).items()
            },
        }
        for name, counts in tally.notes.items()
    }
    align = tally.alignment
    alignment_report: dict[str, Any] = {
        "gold_items": align.gold_items,
        "pred_items": align.pred_items,
        "matched": align.matched,
        "product_tp": align.product_correct,
        "greedy_runs": align.greedy_runs,
        "precision": _ratio(align.product_correct, align.pred_items),
        "recall": _ratio(align.product_correct, align.gold_items),
    }
    align_p, align_r = alignment_report["precision"], alignment_report["recall"]
    alignment_report["f1"] = (
        2 * align_p * align_r / (align_p + align_r) if align_p + align_r else 0.0
    )
    return {
        "eval_version": EVAL_VERSION,
        "records": tally.records,
        "validity": {
            "parsed": tally.parsed,
            "parse_rate": _ratio(tally.parsed, tally.records),
            "repair_used": tally.repair_used,
            "repair_rate": _ratio(tally.repair_used, tally.records),
        },
        "headline": {
            "tp": headline.tp,
            "fp": headline.fp,
            "fn": headline.fn,
            **_prf(headline.tp, headline.fp, headline.fn),
            "strict_rate": _ratio(headline.strict_correct, headline.correct),
            "hallucination_rate": _ratio(
                headline.hallucination, headline.hallucination + headline.null_agree
            ),
        },
        "fields": fields_report,
        "alignment": alignment_report,
        "notes": notes_report,
    }


@dataclass
class ClassificationTally:
    confusion: Counter[tuple[str, str]] = field(default_factory=Counter)

    def absorb(self, other: ClassificationTally) -> None:
        self.confusion.update(other.confusion)


def score_classification(gold_class: str, pred_class: str | None) -> ClassificationTally:
    valid = {member.value for member in EmailClass}
    pred = pred_class if pred_class in valid else "invalid"
    tally = ClassificationTally()
    tally.confusion[(gold_class, pred)] += 1
    return tally


def classification_metrics(tally: ClassificationTally) -> dict[str, Any]:
    confusion = tally.confusion
    total = sum(confusion.values())
    classes = [member.value for member in EmailClass]
    per_class: dict[str, Any] = {}
    f1_values: list[float] = []
    for cls in classes:
        tp = confusion[(cls, cls)]
        fp = sum(count for (g, p), count in confusion.items() if p == cls and g != cls)
        fn = sum(count for (g, p), count in confusion.items() if g == cls and p != cls)
        row = _prf(tp, fp, fn)
        row["support"] = tp + fn
        per_class[cls] = row
        f1_values.append(row["f1"])
    order_total = sum(count for (g, _), count in confusion.items() if g in ORDER_BEARING)
    order_missed = sum(
        count for (g, p), count in confusion.items() if g in ORDER_BEARING and p in NON_ORDER_PRED
    )
    return {
        "eval_version": EVAL_VERSION,
        "records": total,
        "accuracy": _ratio(sum(confusion[(c, c)] for c in classes), total),
        "macro_f1": sum(f1_values) / len(f1_values) if f1_values else 0.0,
        "per_class": per_class,
        "order_missed": order_missed,
        "order_missed_rate": _ratio(order_missed, order_total),
        "invalid_predictions": sum(count for (_, p), count in confusion.items() if p == "invalid"),
        "confusion": {f"{g}->{p}": count for (g, p), count in sorted(confusion.items())},
    }
