# gpt-4o-mini baseline — error analysis (step 2.3 readout)

Run identity: gpt-4o-mini-2024-07-18, temperature 0, structured outputs
strict; prompt-bundle and dataset sha pins live in the run meta files beside
this doc. eval_version=2. Fresh-call spend across both tracks: ~US$0.27.

## Headline

| track | class acc | order_missed | headline F1 | alignment F1 | halluc | attempted |
|---|---|---|---|---|---|---|
| synthetic (n=1000, ext 800) | 0.998 | 0.000 | 0.8485 [0.838, 0.859] | 0.759 | 0.069 | 800/800 |
| human (n=65, ext 57) | 0.846 | 0.105 | 0.8211 [0.767, 0.869] | 0.840 | 0.137 | 51/57* |

\*six gold orders were classified non-order and score as empty extractions
(end-to-end accounting). JSON validity itself was perfect: 851/851 extract
calls parsed strictly, zero repairs — structured outputs never emitted a
malformed object.

## Failure taxonomy

1. **Trailing punctuation and glue absorption — the dominant family.**
   address F1 0.480 (193 wrong), date 0.592 (256 wrong), PO 48 wrong. Spans
   return with sentence tails attached: "Eagle Farm store.", "2 June would
   suit us.", "MPO/7840." strict_rate = 1.0 confirms the reading: whatever
   matches, matches byte-exact; everything else missed the span boundary,
   and punctuation-preserving normalization gave no free points.

2. **List-line segmentation.** product_text 0.759 with 398 wrong spans:
   quantity-first list lines get stuffed whole into product_text. Layout
   slices agree — dash_list 0.806 and x_list 0.817 versus reverse_list and
   prose both above 0.849: a " – "-delimited product span is trivially
   segmentable, a quantity-first one is not. Trap lines are the extreme:
   match_rate 1.000 and quantity recall 1.000, but product recall 0.444 and
   unit 0.578 — comprehension intact, segmentation broken. This also
   explains the alignment reversal (synthetic 0.759 < human 0.840):
   synthetic list layouts and traps are harder to segment than natural
   prose.

3. **Gold-null guessing, including literal "null" strings.** Synthetic unit
   hallucination rate 0.25 (partly the literal string "null" under strict
   mode). On human the family explodes: quantity 0.57, unit 0.83, buyer
   0.67 of gold-null slots filled. The eval caught the exact guess the
   authoring adjudication forbade: "a couple of rolls" (gold null)
   predicted as 2.

4. **OOD classification collapse — the largest track gap.** All six missed
   human orders went to inquiry; their subjects embed questions ("is email
   the right channel?", "packing peanuts?", "plus a question"). The
   discriminating clause that wins the synthetic quote-lookalike case (a
   quote listing products is still an inquiry) backfires on polite blended
   order-plus-question emails. Three further new_order→amendment confusions
   ("same as last time" phrasing) cost no extraction — both classes are
   order-bearing. Synthetic misroutes: 2/1000, both new_order→amendment,
   negligible; the two records are printed in this commit's run log.

5. **Notes fields (non-headline).** Token F1 0.590 / 0.777 synthetic falls
   to 0.288 / 0.250 on human; glue prefixes retained ("Just a heads up:").
   Recorded; excluded from headline by design (step 1.3 decision 5).

## Metric footnotes

- product_text slot F1 and alignment F1 are the same number by construction
  (identical tp; the slot's fp/fn denominators equal pred/gold item
  counts). Both are printed for readability; treat them as one measurement.
- product_text hallucination_rate reads 1.00 whenever any predicted item
  goes unmatched: gold product is never null, so the denominator contains
  no null_agree. It is an existence flag, not a rate.

## SPEC target preview (to be locked or revised in the 2.5 milestone)

- Extraction micro-F1 provisional ≥ 0.92: prompted gpt-4o-mini lands
  0.8485 — the absolute provisional was optimistic; the binding comparison
  (fine-tune ≥ baseline − 2 pts) stands.
- Order-missed ≤ 1%: holds in-distribution (0.0%); fails ten-fold on the
  human slice (10.5%).

## Why this motivates the fine-tune

The three dominant families — punctuation/glue tails, list-line
segmentation, gold-null guessing — are verbatim-discipline errors, exactly
what SFT on truth-first verbatim gold teaches. Comprehension is already
solved (quantity F1 0.997). The gap is discipline, not understanding: the
cleanest possible setup for a small fine-tuned model.
