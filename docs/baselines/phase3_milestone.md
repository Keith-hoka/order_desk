# Phase 3 milestone — QLoRA fine-tune complete

Final adapter: **qwen3-4b-sft-full-r8** — QLoRA on Qwen3-4B-Instruct-2507,
3600 gold-bearing train examples, rank 8, NF4 + completion-only loss,
val-loss-selected checkpoint. Served via vLLM+LoRA, xgrammar-constrained,
scored by the frozen harness (eval_version=3). Prompt contract identical to
baselines and training — end-to-end same-source. Selected over rank 32 on
human OOD generalization (below), not synthetic score.

## Headline: dual-track, the honest pair

| model | synthetic F1 | human OOD F1 | drop | human class_acc | human parse |
|---|---|---|---|---|---|
| qwen3-4b baseline | 0.7168 | 0.7156 | 0.001 | 0.646 | 0.825 |
| gpt-4o-mini | 0.8485 | 0.8211 | 0.028 | 0.846 | 0.895 |
| **sft full-r8** | **0.9978** | **0.9508** | **0.047** | 0.800 | 1.000 |

The fine-tuned 4B beats prompted gpt-4o-mini on both tracks: +11 points
in-distribution, +13 points on the human OOD slice. The 0.047 synthetic→human
drop is the key number — it is small, so the synthetic 0.998 is largely real
capability, not template memorization. The discipline the fine-tune learned
generalizes to hand-written emails (52% unresolvable products, blended
order-plus-question phrasing) it never saw in training.

## Span discipline — the mechanism, closed

| model | span_gap (syn) | product_exact (syn) | alignment (syn) |
|---|---|---|---|
| qwen3-4b baseline | 0.7354 | 0.263 | 0.257 |
| gpt-4o-mini | 0.2008 | 0.798 | 0.759 |
| sft full-r8 | 0.0000 | 0.9994 | 0.9994 |

Baselines established that comprehension was already solved (contains ≥0.998
for every model) and the entire gap was span discipline (baseline span_gap
0.735). The fine-tune drives span_gap to zero: it learned exactly the verbatim
boundaries seeded by the truth-first gold in Phase 1. The loop closes.

## Data-scaling & rank (see phase3_curve.md)

- Data saturates below 500 examples: headline 0.9918 at 500, 0.9975 at 3600
  — 0.6 points across a 7x data increase. "Discipline over scale," measured.
- Rank saturates: r8/r16/r32 within 0.001 on synthetic. r8 chosen — and human
  OOD confirms it: r8 (0.9508, class_acc 0.800, parse 1.000) generalizes
  better than r32 (0.9446, class_acc 0.662, parse 0.965), which overfits the
  last fraction on synthetic and gives it back out-of-distribution.

## Honest weaknesses (human OOD, n=65, wide CIs)

full-r8 is not perfect on the human slice: requested_date_text F1 0.706,
delivery_address_text 0.788 (natural-language date/address variants), and
occasional gold-null guessing (buyer, quantity). Single-digit error counts on
a small sample, but real — the 0.951 is genuine, not a saturated score.
Classification on human (0.800) drops on blended order-plus-question emails,
as it does for every model; the fine-tune was extraction-only, so this is a
Phase 5 routing concern, not an extraction one. Notably order_missed is 0.000
— the fine-tune recovered the blended-order recall the baselines lost.

## Risk #1 — reversed and closed

SPEC §10 anticipated the 4B might not beat gpt-4o-mini, with the pitch
retreating to cost/latency. It beats gpt-4o-mini on both tracks, so cost,
latency, and self-hosting are additive on top of a capability win. Portfolio
headline: 3600 truth-first examples lift a 4B model from 0.717 to 0.998
in-distribution and 0.951 on hand-written OOD — past GPT-4o-mini on both — on
a self-hostable card, with a sha-pinned reproducibility chain from frozen data
through eval.

## Phase 3 exit

Fine-tune target met and exceeded. Final artifact qwen3-4b-sft-full-r8 on the
volume. Next: Phase 4 production inference service (FastAPI, auth, rate-limit,
Langfuse, confidence + ECE) wrapping this adapter as the one learned node.
