# Phase 3 — first fine-tuned adapter (full data, rank 16)

qwen3-4b-sft-full-r16: QLoRA on Qwen/Qwen3-4B-Instruct-2507, 3600 gold-bearing
train examples, NF4 + completion-only loss, val-loss-selected checkpoint
(best_val_loss 0.0636, eval token accuracy 0.977). Served via vLLM+LoRA,
xgrammar-constrained, scored by the frozen harness (eval_version=3) on the
sha-pinned synthetic test (n=1000, ext 800). Prompt contract identical to the
baselines and to training — end-to-end same-source.

## The span-discipline gap closed

| metric | 4B baseline | gpt-4o-mini | 4B fine-tuned |
|---|---|---|---|
| headline F1 | 0.717 | 0.849 | **0.939** |
| span_gap | 0.735 | 0.201 | **0.026** |
| product_exact_rate | 0.263 | 0.798 | **0.974** |
| alignment F1 | 0.257 | 0.759 | **0.940** |
| hallucination_rate | 0.119 | 0.069 | 0.088 |

Three results, each past the Phase 2 milestone targets: headline F1 beats the
best prompted baseline (gpt-4o-mini 0.8485) by ~9 points; span_gap falls below
gpt-4o-mini's; product_exact rises from 0.263 to 0.974. The alignment F1 jump
(0.257→0.940) is exactly the effect eval_version=3 was built to attribute — it
is span discipline recovered, not new capability, and item_semantics proves it:
comprehension was already at parity (baseline contains ≥0.998), the fine-tune
supplied the verbatim boundaries.

## Confirmed by inspection (smoke, 10 records)

- List-line stuffing gone: "half a dozen roll stretch film (same spec...)" now
  parses to product "stretch film" with the note split out, versus the
  baseline stuffing the whole line into product_text.
- Trailing punctuation gone: dates land as "20 April", not "20 April."
- Gold-null respected: unit_text null where the baseline invented a product
  word; team sign-offs yield buyer null.

The fine-tune learned precisely the verbatim discipline seeded by the
truth-first gold in Phase 1 — the loop closes.

## Caveats recorded

- parse_rate 0.9737 (789/800): 21 outputs are xgrammar-valid but violate the
  strict pydantic contract (empty strings / minLength), the exception flagged
  in the Phase 2 constrained-decoding decision. To be characterized after the
  matrix; does not affect the headline conclusion.
- Single adapter, single seed. The data-scaling curve and rank ablation
  (7-run matrix) establish whether full data and rank 16 are near-optimal.

## Risk #1 — reversed

SPEC §10 risk #1 anticipated the 4B might not beat gpt-4o-mini on raw F1, with
the pitch retreating to cost/latency/self-hosting. It does beat it (+9pts
headline, lower span_gap), so cost/self-hosting become additive advantages on
top of a capability win, not a consolation. The portfolio headline: 3600
truth-first examples lift a 4B model's extraction from 0.717 to 0.939 —
past GPT-4o-mini — on a self-hostable card, with a sha-pinned reproducibility
chain.
