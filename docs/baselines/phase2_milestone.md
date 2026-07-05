# Phase 2 milestone — three-way baselines

Three prompted contestants under one snapshot-pinned prompt contract
(schema-derived extraction prompt, hand-authored class definitions), scored
by the frozen eval harness (eval_version=3) against the sha-pinned synthetic
(n=1000, ext 800) and human OOD (n=65, ext 57) sets. Per-run meta and full
reports sit beside this file. No fine-tuning yet; these are the numbers the
Phase 3 fine-tune must beat.

## Headline (synthetic)

| model | class acc | order_missed | headline F1 | alignment F1 | halluc | parse_rate |
|---|---|---|---|---|---|---|
| gpt-4o-mini | 0.998 | 0.000 | **0.8485** [0.838, 0.859] | 0.759 | 0.069 | 1.000 |
| qwen3-30b-a3b (xgrammar) | 0.999 | 0.001 | 0.7708 [0.759, 0.781] | 0.328 | 0.069 | 0.999 |
| qwen3-4b (xgrammar) | 0.982 | 0.016 | 0.7168 [0.705, 0.727] | 0.257 | 0.982 | 0.982 |
| qwen3-4b (free) | 0.982 | 0.016 | 0.7167 [0.705, 0.727] | 0.257 | 0.982 | 0.982 |

## Human OOD

| model | class acc | order_missed | headline F1 | alignment F1 | parse_rate |
|---|---|---|---|---|---|
| gpt-4o-mini | 0.846 | 0.105 | 0.8211 | 0.840 | 0.895 |
| qwen3-30b-a3b (xgrammar) | 0.862 | 0.105 | 0.8187 | 0.588 | 0.895 |
| qwen3-4b (xgrammar) | 0.646 | 0.175 | 0.7156 | 0.597 | 0.825 |

## The central finding: the gap is span discipline, not comprehension

The segmentation-independent diagnostic (item_semantics, eval_version=3;
line items anchored by quantity+unit, product scored exact / contains /
span_gap) resolves the alignment collapse:

| model | product exact | product contains | span_gap | unit_hit | matched |
|---|---|---|---|---|---|
| gpt-4o-mini | 0.798 | 0.999 | 0.201 | 1.000 | 1439 |
| qwen3-30b-a3b | 0.333 | 0.998 | 0.665 | 1.000 | 1380 |
| qwen3-4b | 0.263 | 0.999 | 0.735 | 1.000 | 1304 |

On matched items all three models contain the correct product string
≥99.8% of the time — comprehension is essentially solved across the board.
What separates them is span cleanliness: qwen3-4b emits the right product
buried under a quantity/unit prefix ("4 carton MLR-PLY-502") on 73.5% of
items, which is exactly why its alignment F1 (0.257) craters while its
headline F1 (0.717) does not. The span_gap column is the size of the prize
for a fine-tune that teaches verbatim boundaries: ~0.74 for the 4B target.

Alignment F1 is retained but demoted to a diagnostic — it entangles
segmentation and matching, so a fine-tune fixing spans will make it jump far
more than the underlying extraction improves. Headline micro-F1 stays the
bound metric; item_semantics attributes any Phase 3 gain to span discipline
versus semantics. Denominator note: matched < anchorable_gold (1657) because
items whose quantity/unit are wrong cannot be anchored; their product
quality is outside this diagnostic.

## Failure taxonomy (from smoke + slice inspection)

1. **Quantity-first stuffing — dominant, worst on the small model.** 13/14
   list lines stuffed on 4B, 12/14 on 30B, 4/14 on gpt-4o-mini. Product
   words also leak into unit_text on both Qwen models ("poly mailers").
2. **Trailing punctuation / glue absorption (all three).** "10 July.",
   "2 June would suit us" — the same span-boundary failure at order level.
3. **Gold-null guessing.** gpt-4o-mini emits the literal string "null"
   under strict mode (Qwen never does); Qwen echoes product fragments into
   item_notes/notes.
4. **OOD classification collapse.** All models lose blended
   order-plus-question emails to inquiry on the human slice; 4B collapses
   hardest (acc 0.646, order_missed 0.175).

## Constrained decoding: validity insurance, not a quality lever

qwen3-4b xgrammar and free are byte-identical on headline, alignment, and
item_semantics; xgrammar only lifts parse_rate. Decision: constrained
decoding is retained for Phase 4 serving as a validity guarantee, not
carried as a quality ablation. The Phase 2 quality story is a single line
per model (xgrammar).

## SPEC provisional targets — locked / revised

- **Extraction headline micro-F1.** Provisional ≥ 0.92 was optimistic:
  prompted gpt-4o-mini lands 0.8485. Revised — the binding requirement is
  the documented comparison, fine-tune ≥ best prompted baseline (0.8485)
  on synthetic headline F1, with no per-field regression beyond threshold.
- **span_gap.** New bound target: the fine-tune drives 4B span_gap from
  0.735 toward gpt-4o-mini's 0.201 or below; this is the primary evidence
  of learned verbatim discipline.
- **Classification macro-F1 ≥ 0.93 / accuracy ≥ 0.95.** Holds
  in-distribution for all three (≥ 0.978). The human slice's per-class
  support is 2–3, so accuracy is its headline there and macro-F1 is
  reference only.
- **Order-missed ≤ 1%.** Holds in-distribution for gpt-4o-mini/30B (≤ 0.1%),
  borderline for 4B (1.6%); fails ten-fold on the human slice for every
  model — an OOD classification problem for Phase 5 routing to absorb, not
  an extraction problem.

## Escalation gate (target selection)

Fine-tune target stays qwen3-4b-instruct-2507. It is revisited only if,
after Phase 3, the fine-tuned 4B both (a) misses the absolute quality floor
and (b) clearly loses to qwen3-30b-a3b zero-shot on synthetic headline F1.
Escalation order is qwen3-8b (dense) before qwen3-30b-a3b (MoE) — the MoE
SFT complexity is bought last, and only on evidence, never on vibes.

## Risk #1 resolution (from SPEC §10)

A fine-tuned 4B may not beat gpt-4o-mini on raw headline F1. That is not a
kill condition, and the baselines sharpen the actual pitch: comprehension is
already at parity (contains ≥ 0.998 across models), so the fine-tune's job
is verbatim discipline (the 0.74 span_gap) plus cost, latency, and
self-hosting/privacy — not raw capability. The story is the span_gap closing
on a 7.5x-smaller self-hostable model, reported on both the synthetic and
human tracks, with the cost curve (Phase 2 cloud spend: gpt-4o-mini
~US$0.27 for both sets; Qwen GPU-hours on Modal) as the economic axis.
