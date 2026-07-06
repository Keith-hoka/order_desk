"""Per-field confidence from token logprobs (Phase 4).

Aligns generated tokens to extracted field values by character span, then
aggregates each field's token logprobs into a confidence score. The score is
the geometric mean of token probabilities over the field's span, i.e.
exp(mean(logprob)); a field with no covering tokens (e.g. a null value, which
occupies no value characters) gets a conventional confidence for the null
decision itself, computed from the tokens spanning the JSON null literal.

Token->char offsets are reconstructed by concatenating token strings in order
and tracking cumulative length. vLLM token strings reproduce the raw text
exactly when concatenated, so a field value's character span maps to the
token index range whose cumulative spans overlap it. Shadowed substrings (a
short value that also appears inside a longer one) are disambiguated by
scanning for the value at or after the position where the enclosing JSON key
was emitted.
"""

from __future__ import annotations

import json
import math
from typing import Any

from order_desk.extract_client import TokenLogprob
from order_desk.schemas import ExtractedOrder

ORDER_FIELDS = (
    "customer_po_text",
    "requested_date_text",
    "delivery_address_text",
    "buyer_name_text",
    "notes",
)
ITEM_FIELDS = ("product_text", "quantity", "unit_text", "unit_price_text", "item_notes")


def _token_char_spans(tokens: list[TokenLogprob]) -> list[tuple[int, int]]:
    """Cumulative (start, end) char offsets for each token in concatenation order."""
    spans: list[tuple[int, int]] = []
    cursor = 0
    for tok in tokens:
        length = len(tok.token)
        spans.append((cursor, cursor + length))
        cursor += length
    return spans


def _reconstructed_text(tokens: list[TokenLogprob]) -> str:
    return "".join(tok.token for tok in tokens)


def _confidence_over_span(
    tokens: list[TokenLogprob],
    token_spans: list[tuple[int, int]],
    start: int,
    end: int,
) -> float | None:
    """Geometric mean of token probabilities for tokens overlapping [start, end)."""
    logprobs = [
        tok.logprob
        for tok, (t_start, t_end) in zip(tokens, token_spans, strict=True)
        if t_start < end and t_end > start
    ]
    if not logprobs:
        return None
    return math.exp(sum(logprobs) / len(logprobs))


def _find_value_span(text: str, needle: str, search_from: int) -> tuple[int, int] | None:
    idx = text.find(needle, search_from)
    if idx == -1:
        idx = text.find(needle)  # fall back to first occurrence
        if idx == -1:
            return None
    return idx, idx + len(needle)


def _key_position(text: str, key: str, search_from: int) -> int:
    idx = text.find(f'"{key}"', search_from)
    return idx if idx != -1 else search_from


def field_confidences(
    result_raw: str, tokens: list[TokenLogprob], parsed: ExtractedOrder
) -> dict[str, float]:
    """Flat field-path -> confidence. Values located in the reconstructed text."""
    recon = _reconstructed_text(tokens)
    spans = _token_char_spans(tokens)
    text = recon if recon else result_raw
    out: dict[str, float] = {}
    cursor = 0

    def value_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    def emit(path: str, key: str, value: Any) -> None:
        nonlocal cursor
        cursor = _key_position(text, key, cursor)
        needle = value_json(value)
        span = _find_value_span(text, needle, cursor)
        if span is None:
            return
        conf = _confidence_over_span(tokens, spans, span[0], span[1])
        if conf is not None:
            out[path] = conf
        cursor = span[1]

    dumped = parsed.model_dump()
    for field in ORDER_FIELDS:
        emit(field, field, dumped[field])
    for i, item in enumerate(dumped["line_items"]):
        for field in ITEM_FIELDS:
            emit(f"line_items.{i}.{field}", field, item[field])
    return out


def overall_confidence(field_confs: dict[str, float]) -> float:
    """Geometric mean across fields; 1.0 for an empty set (no claims to doubt)."""
    if not field_confs:
        return 1.0
    return math.exp(sum(math.log(max(c, 1e-12)) for c in field_confs.values()) / len(field_confs))
