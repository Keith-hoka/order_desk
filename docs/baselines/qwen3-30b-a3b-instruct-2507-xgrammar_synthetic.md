# Eval report — qwen3-30b-a3b-instruct-2507-xgrammar on synthetic

- eval_version: 3
- dataset: n=1000 (extraction 800), sha256 b71e122a36272df1
- bootstrap: 1000 iterations, seed 20260708

## Classification

- accuracy: 0.9990 [0.9970, 1.0000]
- macro_f1: 0.9989 [0.9962, 1.0000]
- order_missed_rate: 0.0013 (1 missed)
- invalid_predictions: 0

| class | precision | recall | f1 | support |
|---|---|---|---|---|
| new_order | 1.0000 | 0.9986 | 0.9993 | 700 |
| amendment | 1.0000 | 1.0000 | 1.0000 | 100 |
| cancellation | 1.0000 | 1.0000 | 1.0000 | 50 |
| inquiry | 0.9901 | 1.0000 | 0.9950 | 100 |
| other | 1.0000 | 1.0000 | 1.0000 | 50 |

## Extraction

- headline: P 0.7751 / R 0.7665 / F1 0.7708 [0.7593, 0.7814]
- strict_rate: 0.9998   hallucination_rate: 0.0686
- alignment_f1: 0.3283 [0.2916, 0.3635] (matched 1705/1750 gold, 1747 pred, greedy_runs 0)
- validity: attempted 799/800, parse_rate 0.9988, repair_rate 0.0000, extraction_on_non_gold 0

| field | precision | recall | f1 | halluc_rate | accuracy | strict |
|---|---|---|---|---|---|---|
| customer_po_text | 0.9313 | 0.9313 | 0.9313 | 0.0000 | 0.9637 | 1.0000 |
| requested_date_text | 0.7716 | 0.7703 | 0.7709 | 0.0000 | 0.8200 | 1.0000 |
| delivery_address_text | 0.7468 | 0.7784 | 0.7623 | 0.0404 | 0.8738 | 1.0000 |
| buyer_name_text | 0.9248 | 0.9986 | 0.9603 | 0.5091 | 0.9287 | 1.0000 |
| product_text | 0.3286 | 0.3280 | 0.3283 | 1.0000 | 0.3203 | 1.0000 |
| quantity | 0.9982 | 0.9934 | 0.9958 | 0.0345 | 0.9924 | 1.0000 |
| unit_text | 0.9165 | 0.8195 | 0.8653 | 0.1972 | 0.8153 | 0.9991 |
| unit_price_text | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |

| notes field | token_p | token_r | token_f1 |
|---|---|---|---|
| notes | 0.2603 | 0.7027 | 0.3799 |
| item_notes | 0.5611 | 0.9371 | 0.7019 |

## Slices

| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |
|---|---|---|---|---|---|
| class:new_order | 700 | 0.9986 | 700 | 0.7645 | 0.3025 |
| class:amendment | 100 | 1.0000 | 100 | 0.8989 | 0.8947 |
| class:cancellation | 50 | 1.0000 | 0 | -- | -- |
| class:inquiry | 100 | 1.0000 | 0 | -- | -- |
| class:other | 50 | 1.0000 | 0 | -- | -- |
| flag:missing_po | 69 | 1.0000 | 69 | 0.7767 | 0.4167 |
| flag:missing_quantity | 69 | 0.9855 | 69 | 0.6650 | 0.1416 |
| flag:ambiguous_site | 82 | 1.0000 | 82 | 0.7748 | 0.3539 |
| flag:discontinued_item | 55 | 1.0000 | 55 | 0.7605 | 0.2789 |
| flag:qty_below_moq | 28 | 1.0000 | 28 | 0.7233 | 0.1294 |
| flag:qty_above_max | 34 | 1.0000 | 34 | 0.8046 | 0.4270 |
| flag:pack_size_trap | 90 | 1.0000 | 90 | 0.7251 | 0.2432 |
| flag:mention_typo | 48 | 1.0000 | 48 | 0.7632 | 0.2793 |
| flag:unsigned | 93 | 1.0000 | 93 | 0.7393 | 0.3422 |
| flag:prices_stated | 167 | 1.0000 | 167 | 0.8155 | 0.3526 |
| flag:price_mismatch | 25 | 1.0000 | 25 | 0.7879 | 0.2833 |
| route:touchless | 365 | 1.0000 | 365 | 0.7821 | 0.3420 |
| route:clarification | 92 | 0.9891 | 92 | 0.7221 | 0.2386 |
| route:exception | 243 | 1.0000 | 243 | 0.7536 | 0.2716 |
| layout:dash_list | 271 | 1.0000 | 271 | 0.7055 | 0.0509 |
| layout:x_list | 154 | 0.9935 | 154 | 0.7272 | 0.2273 |
| layout:reverse_list | 178 | 1.0000 | 178 | 0.8499 | 0.6369 |
| layout:prose | 97 | 1.0000 | 97 | 0.8534 | 0.6000 |
| po_placement:subject_only | 121 | 1.0000 | 121 | 0.7789 | 0.3533 |
| po_placement:body_only | 141 | 1.0000 | 141 | 0.7897 | 0.3008 |
| po_placement:both | 100 | 1.0000 | 100 | 0.8015 | 0.3083 |

## Trap-line items (recall-oriented)

- records: 90, items: 90, match_rate: 1.0000
- note: unit_price_text omitted: trap lines carry no price by construction

| field | recall |
|---|---|
| product_text | 0.2667 |
| quantity | 1.0000 |
| unit_text | 0.3444 |
