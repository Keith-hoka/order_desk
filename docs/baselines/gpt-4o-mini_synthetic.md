# Eval report — gpt-4o-mini on synthetic

- eval_version: 2
- dataset: n=1000 (extraction 800), sha256 b71e122a36272df1
- bootstrap: 1000 iterations, seed 20260708

## Classification

- accuracy: 0.9980 [0.9950, 1.0000]
- macro_f1: 0.9977 [0.9938, 1.0000]
- order_missed_rate: 0.0000 (0 missed)
- invalid_predictions: 0

| class | precision | recall | f1 | support |
|---|---|---|---|---|
| new_order | 1.0000 | 0.9971 | 0.9986 | 700 |
| amendment | 0.9804 | 1.0000 | 0.9901 | 100 |
| cancellation | 1.0000 | 1.0000 | 1.0000 | 50 |
| inquiry | 1.0000 | 1.0000 | 1.0000 | 100 |
| other | 1.0000 | 1.0000 | 1.0000 | 50 |

## Extraction

- headline: P 0.8447 / R 0.8524 / F1 0.8485 [0.8382, 0.8587]
- strict_rate: 1.0000   hallucination_rate: 0.0689
- alignment_f1: 0.7589 [0.7291, 0.7870] (matched 1726/1750 gold, 1750 pred, greedy_runs 0)
- validity: attempted 800/800, parse_rate 1.0000, repair_rate 0.0000, extraction_on_non_gold 0

| field | precision | recall | f1 | halluc_rate | accuracy | strict |
|---|---|---|---|---|---|---|
| customer_po_text | 0.8863 | 0.8863 | 0.8863 | 0.0000 | 0.9400 | 1.0000 |
| requested_date_text | 0.5917 | 0.5917 | 0.5917 | 0.0000 | 0.6800 | 1.0000 |
| delivery_address_text | 0.4697 | 0.4908 | 0.4800 | 0.0404 | 0.7375 | 1.0000 |
| buyer_name_text | 0.9491 | 1.0000 | 0.9739 | 0.3364 | 0.9537 | 1.0000 |
| product_text | 0.7589 | 0.7589 | 0.7589 | 1.0000 | 0.7486 | 1.0000 |
| quantity | 0.9988 | 0.9958 | 0.9973 | 0.0263 | 0.9948 | 1.0000 |
| unit_text | 0.8950 | 0.8957 | 0.8953 | 0.2517 | 0.8591 | 1.0000 |
| unit_price_text | 0.9580 | 1.0000 | 0.9786 | 0.0118 | 0.9907 | 1.0000 |

| notes field | token_p | token_r | token_f1 |
|---|---|---|---|
| notes | 0.5044 | 0.7105 | 0.5900 |
| item_notes | 0.8664 | 0.7037 | 0.7766 |

## Slices

| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |
|---|---|---|---|---|---|
| class:new_order | 700 | 0.9971 | 700 | 0.8444 | 0.7479 |
| class:amendment | 100 | 1.0000 | 100 | 0.9341 | 1.0000 |
| class:cancellation | 50 | 1.0000 | 0 | -- | -- |
| class:inquiry | 100 | 1.0000 | 0 | -- | -- |
| class:other | 50 | 1.0000 | 0 | -- | -- |
| flag:missing_po | 69 | 1.0000 | 69 | 0.8331 | 0.7949 |
| flag:missing_quantity | 69 | 0.9855 | 69 | 0.7869 | 0.6471 |
| flag:ambiguous_site | 82 | 1.0000 | 82 | 0.8533 | 0.7433 |
| flag:discontinued_item | 55 | 1.0000 | 55 | 0.8653 | 0.7526 |
| flag:qty_below_moq | 28 | 1.0000 | 28 | 0.8277 | 0.6706 |
| flag:qty_above_max | 34 | 1.0000 | 34 | 0.8489 | 0.7079 |
| flag:pack_size_trap | 90 | 1.0000 | 90 | 0.7733 | 0.5541 |
| flag:mention_typo | 48 | 1.0000 | 48 | 0.8039 | 0.5676 |
| flag:unsigned | 93 | 1.0000 | 93 | 0.8070 | 0.7067 |
| flag:prices_stated | 167 | 1.0000 | 167 | 0.8909 | 0.8263 |
| flag:price_mismatch | 25 | 1.0000 | 25 | 0.8771 | 0.8500 |
| route:touchless | 365 | 0.9973 | 365 | 0.8627 | 0.8128 |
| route:clarification | 92 | 0.9891 | 92 | 0.8239 | 0.7071 |
| route:exception | 243 | 1.0000 | 243 | 0.8261 | 0.6775 |
| layout:dash_list | 271 | 1.0000 | 271 | 0.8057 | 0.5968 |
| layout:x_list | 154 | 1.0000 | 154 | 0.8170 | 0.7089 |
| layout:reverse_list | 178 | 1.0000 | 178 | 0.9088 | 0.9554 |
| layout:prose | 97 | 0.9794 | 97 | 0.8840 | 0.8897 |
| po_placement:subject_only | 121 | 1.0000 | 121 | 0.8509 | 0.7967 |
| po_placement:body_only | 141 | 0.9929 | 141 | 0.8701 | 0.7284 |
| po_placement:both | 100 | 0.9900 | 100 | 0.8737 | 0.7273 |

## Trap-line items (recall-oriented)

- records: 90, items: 90, match_rate: 1.0000
- note: unit_price_text omitted: trap lines carry no price by construction

| field | recall |
|---|---|
| product_text | 0.4444 |
| quantity | 1.0000 |
| unit_text | 0.5778 |
