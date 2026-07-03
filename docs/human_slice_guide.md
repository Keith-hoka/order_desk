# Human OOD slice — authoring guide (step 1.8c)

## What this measures
40–70 order emails written by hand against the same fixtures, gold-labelled
by the author, frozen as `data/human/test_human.jsonl`. Every headline result
reports on both tracks: the synthetic split measures in-distribution
performance; this slice detects template overfitting. If the fine-tune wins
on synthetic and collapses here, that is the finding, and it gets reported.

## Contamination posture (disclosed, not pretended away)
The author audited 120 synthetic emails before writing (steps 1.8a–b), so
total isolation is impossible. Rule while authoring: do **not** open
`renderer.py`, `nonorder.py`, or any corpus `.jsonl`. Consult only
`catalog.json` and `customers.json` (you are a customer ordering from them).

## Format
One file: `data/human/authoring.md` (committed — it is the provenance of the
frozen slice). One block per email:

    ### HUM-0001
    From: dana.whitfield@harbourline.com.au
    Sent: 2026-02-11 09:15
    Class: new_order
    Subject: tape for Botany

    Body starts after one blank line. Write like a real customer.

```gold
    { ...ExtractedOrder JSON... }
```

- `Sent` is naive local time; the parser attaches Australia/Sydney. Keep it
  in 2026, business-ish hours.
- `Class` ∈ new_order / amendment / cancellation / inquiry / other.
  new_order and amendment **must** carry a gold fence; the rest must not.
- Senders must be fixture contacts, except `other` may use unknown domains.

## ExtractedOrder JSON — the exact gold shape

Authoritative definitions live in `src/order_desk/schemas.py` (its field
descriptions double as the model-facing prompt) and the CI-pinned snapshot
`tests/snapshots/extracted_order.schema.json`; this section restates them so
nothing else needs opening while you write. Every key is required on every
record: `null` marks anything the email does not state, keys are never
omitted, unknown keys are rejected, empty strings are rejected, and types
are strict — `"quantity": "6"` fails, it must be the integer `6`, and >= 1.

```json
{
  "customer_po_text": "PO-48213",
  "requested_date_text": "by next Friday",
  "delivery_address_text": "Eastern Creek DC",
  "buyer_name_text": "Dana",
  "notes": "tailgate required",
  "line_items": [
    {
      "product_text": "shrink wrap",
      "quantity": 12,
      "unit_text": "rolls",
      "unit_price_text": "$7.80",
      "item_notes": null
    },
    {
      "product_text": "packing tape",
      "quantity": null,
      "unit_text": null,
      "unit_price_text": null,
      "item_notes": "whatever brand is on the shelf"
    }
  ]
}
```

Order level:
- `customer_po_text` — the PO reference exactly as written; null if none.
- `requested_date_text` — the timing phrase verbatim ("by next Friday",
  "ASAP"); never converted to a date.
- `delivery_address_text` — the destination as written, site name or full
  address; null if unstated.
- `buyer_name_text` — the individual placing the order as named in the body
  (sign-offs count); team sign-offs → null.
- `notes` — order-level delivery/handling instructions verbatim; null if
  none.

Per line item:
- `product_text` — the product exactly as the email says it, however vague
  or typo'd; never normalised to a catalog name or SKU.
- `quantity` — integer >= 1; number words become digits ("a dozen" → 12);
  null when no quantity is stated.
- `unit_text` — the unit word as written ("rolls", "ctns"); null if none.
- `unit_price_text` — the per-unit price verbatim including the currency
  symbol ("$7.80"); null if no price is stated.
- `item_notes` — line-specific instructions verbatim; null if none.

new_order gold needs at least one line item. Amendments share the shape and
capture only what the email states: the referenced PO verbatim in
`customer_po_text` (null when you point at "yesterday's order" instead), the
changed line(s) in `line_items` — empty for a pure date change, which lives
in `requested_date_text`. And the standing reminder: every string above must
also appear character-exact in your subject or body (rule 1 below), so write
the email first, then transcribe into gold.

## Gold rules (the ones that bite)
1. Every **string** field in gold must appear character-exact in the subject
   or body — machine-checked. Keep each surface on a single line; a wrapped
   phrase fails containment.
2. `quantity` is an int. "one carton" in prose → `1` in gold; the machine
   cannot check this, you are the authority. Ranges ("40-50 rolls") →
   `quantity: null` (the schema cannot hold a range and never guesses) —
   write a few anyway; the limitation is a finding, not a bug to avoid.
3. Vague products are valuable: "the usual", a typo'd name — `product_text`
   is the vague phrase verbatim; downstream resolution failing is the point.
4. Every gold key present; `null` means the email does not state it. Empty
   strings never.
5. `buyer_name_text`: an individual named in the body (sign-off counts);
   team sign-offs → null.
6. Prices verbatim into `unit_price_text` however you wrote them. Writing a
   deliberately wrong price needs no special marking.
7. Order + question in one email is realistic; if an order is actually being
   placed, `Class: new_order` and extraction proceeds normally.
8. Timing phrases verbatim into `requested_date_text`; no normalization
   truth is recorded (date-parser eval stays synthetic-only, where
   `intended_date` exists).

## Composition
Hard (freeze refuses otherwise): 40–70 total, ≥30 new_order.
Recommended: 45–55 new_order, plus 8–12 non-order if you want classification
OOD signal. Soft targets the builder reports (aim, don't farm): ≥8 no-PO,
≥6 with prices, ≥6 with a missing quantity, ≥5 multi-site customers with no
address, ≥5 unresolvable product mentions, ≥4 piece-count/odd units,
≥6 distinct customers, all 3 tones.

Situational prompts for variety (scenarios, not phrasings): a production
stoppage; a first order from a new contact; "same as last time plus X"; an
old quote's prices pasted in; a delivery window ("between the 10th and
12th"); a typo made at speed; a terse phone-style note; an over-polite
first-time buyer.

## Workflow
Write in sittings. End each sitting:
`uv run python scripts/build_human_slice.py --preview`, then commit
`authoring.md`. When composition is in band, run the builder without flags —
that is the one-time freeze (jsonl + manifest, commit together). After the
freeze, editing `authoring.md` turns CI red by design: the manifest pins both
the jsonl and the authoring hash, and changes go through the
`--refreeze --entry` ritual in `docs/frozen_test_fixlog.md`.

## Scope notes
- `oracle` is null in human records: route/asks/violations are derived at
  eval time by the Phase 5 validator against gold — never stored, so there
  is exactly one oracle implementation for runtime and human eval alike.
- Reply chains, footers, HTML: Phase 6 territory; write standalone plain
  emails here.
