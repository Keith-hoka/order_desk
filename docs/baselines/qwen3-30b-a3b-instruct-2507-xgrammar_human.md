# Eval report — qwen3-30b-a3b-instruct-2507-xgrammar on human

- eval_version: 3
- dataset: n=65 (extraction 57), sha256 c29bd15c281aa056
- bootstrap: 1000 iterations, seed 20260708

## Classification

- accuracy: 0.8615 [0.7692, 0.9385]
- macro_f1: 0.7863 [0.5669, 0.9166]
- order_missed_rate: 0.1053 (6 missed)
- invalid_predictions: 0

| class | precision | recall | f1 | support |
|---|---|---|---|---|
| new_order | 1.0000 | 0.8519 | 0.9200 | 54 |
| amendment | 0.6000 | 1.0000 | 0.7500 | 3 |
| cancellation | 1.0000 | 1.0000 | 1.0000 | 2 |
| inquiry | 0.3000 | 1.0000 | 0.4615 | 3 |
| other | 1.0000 | 0.6667 | 0.8000 | 3 |

## Extraction

- headline: P 0.8476 / R 0.7917 / F1 0.8187 [0.7631, 0.8655]
- strict_rate: 1.0000   hallucination_rate: 0.0726
- alignment_f1: 0.5882 [0.4561, 0.7351] (matched 52/62 gold, 57 pred, greedy_runs 0)
- validity: attempted 51/57, parse_rate 0.8947, repair_rate 0.0000, extraction_on_non_gold 0

| field | precision | recall | f1 | halluc_rate | accuracy | strict |
|---|---|---|---|---|---|---|
| customer_po_text | 0.7941 | 0.7714 | 0.7826 | 0.0000 | 0.8596 | 1.0000 |
| requested_date_text | 0.7500 | 0.7500 | 0.7500 | 0.0204 | 0.9474 | 1.0000 |
| delivery_address_text | 0.7647 | 0.7647 | 0.7647 | 0.0250 | 0.9123 | 1.0000 |
| buyer_name_text | 0.9600 | 0.8889 | 0.9231 | 0.6667 | 0.8596 | 1.0000 |
| product_text | 0.6140 | 0.5645 | 0.5882 | 1.0000 | 0.5224 | 1.0000 |
| quantity | 0.9600 | 0.8889 | 0.9231 | 0.3333 | 0.8667 | 1.0000 |
| unit_text | 0.9556 | 0.8600 | 0.9053 | 0.2000 | 0.8500 | 1.0000 |
| unit_price_text | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |

| notes field | token_p | token_r | token_f1 |
|---|---|---|---|
| notes | 0.0954 | 0.8621 | 0.1718 |
| item_notes | 0.0612 | 0.1731 | 0.0905 |

## Slices

| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |
|---|---|---|---|---|---|
| class:new_order | 54 | 0.8519 | 54 | 0.8211 | 0.5913 |
| class:amendment | 3 | 1.0000 | 3 | 0.7692 | 0.5000 |
| class:cancellation | 2 | 1.0000 | 0 | -- | -- |
| class:inquiry | 3 | 1.0000 | 0 | -- | -- |
| class:other | 3 | 0.6667 | 0 | -- | -- |
