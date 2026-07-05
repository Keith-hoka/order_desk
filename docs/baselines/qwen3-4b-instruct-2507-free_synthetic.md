# Eval report — qwen3-4b-instruct-2507-free on synthetic

- eval_version: 3
- dataset: n=1000 (extraction 800), sha256 b71e122a36272df1
- bootstrap: 1000 iterations, seed 20260708

## Classification

- accuracy: 0.9820 [0.9740, 0.9890]
- macro_f1: 0.9784 [0.9669, 0.9875]
- order_missed_rate: 0.0163 (13 missed)
- invalid_predictions: 0

| class | precision | recall | f1 | support |
|---|---|---|---|---|
| new_order | 1.0000 | 0.9757 | 0.9877 | 700 |
| amendment | 0.9519 | 0.9900 | 0.9706 | 100 |
| cancellation | 0.9804 | 1.0000 | 0.9901 | 50 |
| inquiry | 0.8929 | 1.0000 | 0.9434 | 100 |
| other | 1.0000 | 1.0000 | 1.0000 | 50 |

## Extraction

- headline: P 0.7131 / R 0.7203 / F1 0.7167 [0.7052, 0.7274]
- strict_rate: 0.9998   hallucination_rate: 0.1192
- alignment_f1: 0.2569 [0.2261, 0.2921] (matched 1672/1750 gold, 1722 pred, greedy_runs 0)
- validity: attempted 787/800, parse_rate 0.9825, repair_rate 0.0000, extraction_on_non_gold 0

| field | precision | recall | f1 | halluc_rate | accuracy | strict |
|---|---|---|---|---|---|---|
| customer_po_text | 0.5857 | 0.5829 | 0.5843 | 0.0000 | 0.7800 | 1.0000 |
| requested_date_text | 0.6564 | 0.6459 | 0.6511 | 0.0058 | 0.7212 | 1.0000 |
| delivery_address_text | 0.7249 | 0.7441 | 0.7344 | 0.0404 | 0.8575 | 1.0000 |
| buyer_name_text | 0.9483 | 0.9826 | 0.9651 | 0.3364 | 0.9387 | 1.0000 |
| product_text | 0.2590 | 0.2549 | 0.2569 | 1.0000 | 0.2478 | 1.0000 |
| quantity | 0.9975 | 0.9759 | 0.9866 | 0.0545 | 0.9749 | 1.0000 |
| unit_text | 0.8075 | 0.8850 | 0.8445 | 0.5711 | 0.7741 | 0.9991 |
| unit_price_text | 1.0000 | 0.9644 | 0.9819 | 0.0000 | 0.9923 | 1.0000 |

| notes field | token_p | token_r | token_f1 |
|---|---|---|---|
| notes | 0.4505 | 0.8044 | 0.5775 |
| item_notes | 0.6811 | 0.7450 | 0.7116 |

## Slices

| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |
|---|---|---|---|---|---|
| class:new_order | 700 | 0.9757 | 700 | 0.7139 | 0.2319 |
| class:amendment | 100 | 0.9900 | 100 | 0.7746 | 0.8079 |
| class:cancellation | 50 | 1.0000 | 0 | -- | -- |
| class:inquiry | 100 | 1.0000 | 0 | -- | -- |
| class:other | 50 | 1.0000 | 0 | -- | -- |
| flag:missing_po | 69 | 0.9855 | 69 | 0.7020 | 0.2541 |
| flag:missing_quantity | 69 | 0.9275 | 69 | 0.6232 | 0.2229 |
| flag:ambiguous_site | 82 | 0.9878 | 82 | 0.6949 | 0.2264 |
| flag:discontinued_item | 55 | 0.9455 | 55 | 0.6960 | 0.1348 |
| flag:qty_below_moq | 28 | 0.9643 | 28 | 0.6971 | 0.1647 |
| flag:qty_above_max | 34 | 0.9706 | 34 | 0.7118 | 0.1921 |
| flag:pack_size_trap | 90 | 0.9778 | 90 | 0.6730 | 0.1587 |
| flag:mention_typo | 48 | 0.9792 | 48 | 0.6987 | 0.2182 |
| flag:unsigned | 93 | 0.9892 | 93 | 0.6832 | 0.2539 |
| flag:prices_stated | 167 | 0.9701 | 167 | 0.7544 | 0.2493 |
| flag:price_mismatch | 25 | 0.9600 | 25 | 0.7315 | 0.2034 |
| route:touchless | 365 | 0.9863 | 365 | 0.7374 | 0.2776 |
| route:clarification | 92 | 0.9565 | 92 | 0.6710 | 0.2308 |
| route:exception | 243 | 0.9671 | 243 | 0.6948 | 0.1733 |
| layout:dash_list | 271 | 0.9668 | 271 | 0.6646 | 0.0693 |
| layout:x_list | 154 | 0.9805 | 154 | 0.6752 | 0.1027 |
| layout:reverse_list | 178 | 0.9888 | 178 | 0.7989 | 0.5235 |
| layout:prose | 97 | 0.9691 | 97 | 0.7672 | 0.3819 |
| po_placement:subject_only | 121 | 0.9752 | 121 | 0.6630 | 0.2282 |
| po_placement:body_only | 141 | 0.9787 | 141 | 0.7558 | 0.2141 |
| po_placement:both | 100 | 0.9900 | 100 | 0.7122 | 0.2099 |

## Trap-line items (recall-oriented)

- records: 90, items: 90, match_rate: 0.9444
- note: unit_price_text omitted: trap lines carry no price by construction

| field | recall |
|---|---|
| product_text | 0.1444 |
| quantity | 0.9444 |
| unit_text | 0.6444 |
