# Phase 3 — data-scaling curve & rank ablation (synthetic)

All adapters QLoRA on Qwen3-4B-Instruct-2507, served via vLLM+LoRA (unified
six-adapter endpoint, parse_rate 1.0 throughout), xgrammar-constrained,
scored by the frozen harness (eval_version=3) on the sha-pinned synthetic
test (n=1000, ext 800). Same prompt contract as training and baselines.

## Data-scaling curve (rank 16)

| data | headline F1 | span_gap | product_exact | alignment | halluc |
|---|---|---|---|---|---|
| 500 | 0.9918 | 0.0019 | 0.9969 | 0.9914 | 0.0224 |
| 1000 | 0.9957 | 0.0006 | 0.9982 | 0.9994 | 0.0160 |
| 2000 | 0.9974 | 0.0012 | 0.9982 | 0.9983 | 0.0100 |
| full (3600) | 0.9975 | 0.0006 | 0.9994 | 0.9994 | 0.0107 |

Saturates below 500: from 500 to 3600 headline rises only 0.6 points, and
span_gap is already ~0.002 at 500. The verbatim discipline the fine-tune
teaches is learned almost immediately; more data barely moves it. Validates
"discipline over scale" — and the earlier decision not to scale to 10000.

## Rank ablation (full data)

| rank | headline F1 | span_gap | product_exact | alignment | halluc |
|---|---|---|---|---|---|
| 8 | 0.9978 | 0.0000 | 0.9994 | 0.9994 | 0.0093 |
| 16 | 0.9975 | 0.0006 | 0.9994 | 0.9994 | 0.0107 |
| 32 | 0.9989 | 0.0000 | 1.0000 | 1.0000 | 0.0053 |

Rank saturates: r8 to r32 differ by 0.001 (noise), span_gap zero across the
board. Rank 8 is sufficient; higher rank buys nothing on this task.

## References (from Phase 2)

| model | headline F1 | span_gap | product_exact |
|---|---|---|---|
| gpt-4o-mini | 0.8485 | 0.2008 | 0.7978 |
| qwen3-4b baseline | 0.7168 | 0.7354 | 0.2630 |

## Caveat — these are in-distribution numbers

Synthetic test and training share one generator, so headline 0.99 /
product_exact 1.000 very likely include template overfitting: the model may
have learned this renderer's regularities, not only generalizable
extraction. Synthetic cannot separate the two. The human-authored OOD slice
is the test of real generalization, evaluated next; the honest headline is
the pair (synthetic in-distribution, human OOD).
