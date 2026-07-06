# Eval report — qwen3-4b-sft-full-r8-xgrammar on human

- eval_version: 3
- dataset: n=65 (extraction 57), sha256 c29bd15c281aa056
- bootstrap: 1000 iterations, seed 20260708

## Classification

- accuracy: 0.8000 [0.7073, 0.8923]
- macro_f1: 0.5646 [0.4284, 0.8033]
- order_missed_rate: 0.0000 (0 missed)
- invalid_predictions: 0

| class | precision | recall | f1 | support |
|---|---|---|---|---|
| new_order | 1.0000 | 0.8148 | 0.8980 | 54 |
| amendment | 0.2308 | 1.0000 | 0.3750 | 3 |
| cancellation | 0.6667 | 1.0000 | 0.8000 | 2 |
| inquiry | 0.6000 | 1.0000 | 0.7500 | 3 |
| other | 0.0000 | 0.0000 | 0.0000 | 3 |

## Extraction

- headline: P 0.9302 / R 0.9722 / F1 0.9508 [0.9268, 0.9726]
- strict_rate: 0.9964   hallucination_rate: 0.0895
- alignment_f1: 0.9449 [0.8926, 0.9841] (matched 60/62 gold, 65 pred, greedy_runs 0)
- validity: attempted 57/57, parse_rate 1.0000, repair_rate 0.0000, extraction_on_non_gold 0

| field | precision | recall | f1 | halluc_rate | accuracy | strict |
|---|---|---|---|---|---|---|
| customer_po_text | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| requested_date_text | 0.6667 | 0.7500 | 0.7059 | 0.0408 | 0.9298 | 1.0000 |
| delivery_address_text | 0.8125 | 0.7647 | 0.7879 | 0.0000 | 0.9298 | 1.0000 |
| buyer_name_text | 0.9643 | 1.0000 | 0.9818 | 0.6667 | 0.9649 | 1.0000 |
| product_text | 0.9231 | 0.9677 | 0.9449 | 1.0000 | 0.8955 | 0.9833 |
| quantity | 0.9153 | 1.0000 | 0.9558 | 0.6250 | 0.9194 | 1.0000 |
| unit_text | 0.9434 | 1.0000 | 0.9709 | 0.2727 | 0.9508 | 1.0000 |
| unit_price_text | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |

| notes field | token_p | token_r | token_f1 |
|---|---|---|---|
| notes | 0.1477 | 0.8966 | 0.2537 |
| item_notes | 0.0000 | 0.0000 | 0.0000 |

## Slices

| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |
|---|---|---|---|---|---|
| class:new_order | 54 | 0.8148 | 54 | 0.9610 | 0.9593 |
| class:amendment | 3 | 1.0000 | 3 | 0.7200 | 0.5000 |
| class:cancellation | 2 | 1.0000 | 0 | -- | -- |
| class:inquiry | 3 | 1.0000 | 0 | -- | -- |
| class:other | 3 | 0.0000 | 0 | -- | -- |
