# Eval report — qwen3-4b-instruct-2507-free on human

- eval_version: 3
- dataset: n=65 (extraction 57), sha256 c29bd15c281aa056
- bootstrap: 1000 iterations, seed 20260708

## Classification

- accuracy: 0.6462 [0.5381, 0.7538]
- macro_f1: 0.6461 [0.4344, 0.7743]
- order_missed_rate: 0.1754 (10 missed)
- invalid_predictions: 0

| class | precision | recall | f1 | support |
|---|---|---|---|---|
| new_order | 1.0000 | 0.5926 | 0.7442 | 54 |
| amendment | 0.2000 | 1.0000 | 0.3333 | 3 |
| cancellation | 1.0000 | 1.0000 | 1.0000 | 2 |
| inquiry | 0.2143 | 1.0000 | 0.3529 | 3 |
| other | 1.0000 | 0.6667 | 0.8000 | 3 |

## Extraction

- headline: P 0.7819 / R 0.6597 / F1 0.7156 [0.6433, 0.7845]
- strict_rate: 1.0000   hallucination_rate: 0.0899
- alignment_f1: 0.5965 [0.4576, 0.7368] (matched 48/62 gold, 52 pred, greedy_runs 0)
- validity: attempted 47/57, parse_rate 0.8246, repair_rate 0.0000, extraction_on_non_gold 0

| field | precision | recall | f1 | halluc_rate | accuracy | strict |
|---|---|---|---|---|---|---|
| customer_po_text | 0.5000 | 0.4857 | 0.4928 | 0.0000 | 0.6842 | 1.0000 |
| requested_date_text | 0.5000 | 0.6250 | 0.5556 | 0.0612 | 0.8947 | 1.0000 |
| delivery_address_text | 0.7143 | 0.5882 | 0.6452 | 0.0000 | 0.8772 | 1.0000 |
| buyer_name_text | 0.9565 | 0.8148 | 0.8800 | 0.6667 | 0.7895 | 1.0000 |
| product_text | 0.6538 | 0.5484 | 0.5965 | 1.0000 | 0.5152 | 1.0000 |
| quantity | 0.9318 | 0.7593 | 0.8367 | 0.4286 | 0.7377 | 1.0000 |
| unit_text | 0.8919 | 0.6600 | 0.7586 | 0.3636 | 0.6557 | 1.0000 |
| unit_price_text | 1.0000 | 0.7500 | 0.8571 | 0.0000 | 0.9600 | 1.0000 |

| notes field | token_p | token_r | token_f1 |
|---|---|---|---|
| notes | 0.1688 | 0.8966 | 0.2842 |
| item_notes | 0.1818 | 0.0769 | 0.1081 |

## Slices

| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |
|---|---|---|---|---|---|
| class:new_order | 54 | 0.5926 | 54 | 0.7248 | 0.6000 |
| class:amendment | 3 | 1.0000 | 3 | 0.5385 | 0.5000 |
| class:cancellation | 2 | 1.0000 | 0 | -- | -- |
| class:inquiry | 3 | 1.0000 | 0 | -- | -- |
| class:other | 3 | 0.6667 | 0 | -- | -- |
