# Eval report — qwen3-4b-sft-full-r8-xgrammar on synthetic

- eval_version: 3
- dataset: n=1000 (extraction 800), sha256 b71e122a36272df1
- bootstrap: 1000 iterations, seed 20260708

## Classification

- accuracy: 0.9750 [0.9650, 0.9850]
- macro_f1: 0.9178 [0.8858, 0.9467]
- order_missed_rate: 0.0000 (0 missed)
- invalid_predictions: 0

| class | precision | recall | f1 | support |
|---|---|---|---|---|
| new_order | 1.0000 | 0.9971 | 0.9986 | 700 |
| amendment | 0.8000 | 1.0000 | 0.8889 | 100 |
| cancellation | 1.0000 | 1.0000 | 1.0000 | 50 |
| inquiry | 1.0000 | 1.0000 | 1.0000 | 100 |
| other | 1.0000 | 0.5400 | 0.7013 | 50 |

## Extraction

- headline: P 0.9959 / R 0.9997 / F1 0.9978 [0.9969, 0.9986]
- strict_rate: 1.0000   hallucination_rate: 0.0093
- alignment_f1: 0.9994 [0.9982, 1.0000] (matched 1750/1750 gold, 1750 pred, greedy_runs 0)
- validity: attempted 800/800, parse_rate 1.0000, repair_rate 0.0000, extraction_on_non_gold 23

| field | precision | recall | f1 | halluc_rate | accuracy | strict |
|---|---|---|---|---|---|---|
| customer_po_text | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| requested_date_text | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| delivery_address_text | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| buyer_name_text | 0.9691 | 1.0000 | 0.9843 | 0.2000 | 0.9725 | 1.0000 |
| product_text | 0.9994 | 0.9994 | 0.9994 | 0.0000 | 0.9994 | 1.0000 |
| quantity | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| unit_text | 0.9985 | 0.9992 | 0.9989 | 0.0023 | 0.9989 | 1.0000 |
| unit_price_text | 0.9865 | 1.0000 | 0.9932 | 0.0036 | 0.9971 | 1.0000 |

| notes field | token_p | token_r | token_f1 |
|---|---|---|---|
| notes | 0.8950 | 1.0000 | 0.9446 |
| item_notes | 0.9348 | 0.9509 | 0.9428 |

## Slices

| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |
|---|---|---|---|---|---|
| class:new_order | 700 | 0.9971 | 700 | 0.9978 | 0.9994 |
| class:amendment | 100 | 1.0000 | 100 | 0.9970 | 1.0000 |
| class:cancellation | 50 | 1.0000 | 0 | -- | -- |
| class:inquiry | 100 | 1.0000 | 0 | -- | -- |
| class:other | 50 | 0.5400 | 0 | -- | -- |
| flag:missing_po | 69 | 1.0000 | 69 | 0.9951 | 1.0000 |
| flag:missing_quantity | 69 | 1.0000 | 69 | 0.9952 | 1.0000 |
| flag:ambiguous_site | 82 | 0.9878 | 82 | 0.9906 | 1.0000 |
| flag:discontinued_item | 55 | 1.0000 | 55 | 0.9980 | 1.0000 |
| flag:qty_below_moq | 28 | 1.0000 | 28 | 1.0000 | 1.0000 |
| flag:qty_above_max | 34 | 1.0000 | 34 | 0.9971 | 1.0000 |
| flag:pack_size_trap | 90 | 1.0000 | 90 | 0.9978 | 1.0000 |
| flag:mention_typo | 48 | 1.0000 | 48 | 0.9946 | 0.9910 |
| flag:unsigned | 93 | 0.9892 | 93 | 0.9873 | 1.0000 |
| flag:prices_stated | 167 | 1.0000 | 167 | 0.9984 | 0.9974 |
| flag:price_mismatch | 25 | 1.0000 | 25 | 1.0000 | 1.0000 |
| route:touchless | 365 | 0.9973 | 365 | 0.9991 | 1.0000 |
| route:clarification | 92 | 0.9891 | 92 | 0.9936 | 1.0000 |
| route:exception | 243 | 1.0000 | 243 | 0.9973 | 0.9985 |
| layout:dash_list | 271 | 1.0000 | 271 | 0.9984 | 1.0000 |
| layout:x_list | 154 | 0.9935 | 154 | 0.9974 | 0.9973 |
| layout:reverse_list | 178 | 1.0000 | 178 | 0.9973 | 1.0000 |
| layout:prose | 97 | 0.9897 | 97 | 0.9979 | 1.0000 |
| po_placement:subject_only | 121 | 0.9917 | 121 | 0.9956 | 0.9967 |
| po_placement:body_only | 141 | 1.0000 | 141 | 0.9985 | 1.0000 |
| po_placement:both | 100 | 0.9900 | 100 | 0.9986 | 1.0000 |

## Trap-line items (recall-oriented)

- records: 90, items: 90, match_rate: 1.0000
- note: unit_price_text omitted: trap lines carry no price by construction

| field | recall |
|---|---|
| product_text | 1.0000 |
| quantity | 1.0000 |
| unit_text | 1.0000 |
