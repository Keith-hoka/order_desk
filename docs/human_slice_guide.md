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
