# Eval report — gpt-4o-mini on human

- eval_version: 2
- dataset: n=65 (extraction 57), sha256 c29bd15c281aa056
- bootstrap: 1000 iterations, seed 20260708

## Classification

- accuracy: 0.8462 [0.7538, 0.9231]
- macro_f1: 0.7675 [0.5632, 0.8989]
- order_missed_rate: 0.1053 (6 missed)
- invalid_predictions: 0

| class | precision | recall | f1 | support |
|---|---|---|---|---|
| new_order | 1.0000 | 0.8333 | 0.9091 | 54 |
| amendment | 0.5000 | 1.0000 | 0.6667 | 3 |
| cancellation | 1.0000 | 1.0000 | 1.0000 | 2 |
| inquiry | 0.3000 | 1.0000 | 0.4615 | 3 |
| other | 1.0000 | 0.6667 | 0.8000 | 3 |

## Extraction

- headline: P 0.8298 / R 0.8125 / F1 0.8211 [0.7671, 0.8690]
- strict_rate: 1.0000   hallucination_rate: 0.1374
- alignment_f1: 0.8403 [0.7434, 0.9160] (matched 54/62 gold, 57 pred, greedy_runs 0)
- validity: attempted 51/57, parse_rate 0.8947, repair_rate 0.0000, extraction_on_non_gold 0

| field | precision | recall | f1 | halluc_rate | accuracy | strict |
|---|---|---|---|---|---|---|
| customer_po_text | 0.6875 | 0.6286 | 0.6567 | 0.0000 | 0.7719 | 1.0000 |
| requested_date_text | 0.5455 | 0.7500 | 0.6316 | 0.0612 | 0.9123 | 1.0000 |
| delivery_address_text | 0.5000 | 0.4706 | 0.4848 | 0.0500 | 0.8070 | 1.0000 |
| buyer_name_text | 0.9600 | 0.8889 | 0.9231 | 0.6667 | 0.8596 | 1.0000 |
| product_text | 0.8772 | 0.8065 | 0.8403 | 1.0000 | 0.7692 | 1.0000 |
| quantity | 0.9245 | 0.9074 | 0.9159 | 0.5714 | 0.8525 | 1.0000 |
| unit_text | 0.8148 | 0.8800 | 0.8462 | 0.8333 | 0.7419 | 1.0000 |
| unit_price_text | 0.7778 | 0.8750 | 0.8235 | 0.0217 | 0.9630 | 1.0000 |

| notes field | token_p | token_r | token_f1 |
|---|---|---|---|
| notes | 0.1951 | 0.5517 | 0.2883 |
| item_notes | 0.1852 | 0.3846 | 0.2500 |

## Slices

| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |
|---|---|---|---|---|---|
| class:new_order | 54 | 0.8333 | 54 | 0.8303 | 0.8522 |
| class:amendment | 3 | 1.0000 | 3 | 0.6429 | 0.5000 |
| class:cancellation | 2 | 1.0000 | 0 | -- | -- |
| class:inquiry | 3 | 1.0000 | 0 | -- | -- |
| class:other | 3 | 0.6667 | 0 | -- | -- |
