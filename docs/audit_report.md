# Audit report — frozen test subsample (step 1.8)

Sample: n=120 of the frozen test split (n=1000), coverage-first
stratified (data/audit/sample_ids.json). Noise strata are oversampled by
design: every rate below is diagnostic per stratum, not a corpus estimate.

## Label verification

- 120/120 labels_correct, zero findings: the
  expected null result. Gold is derived from truth-first scenarios and
  machine contract-verified; this human pass is a redundant fuse, and a
  finding here would have meant a contract bug. The SPEC §7
  human-certified subsample is hereby certified.

## Realism (on-sample)

- overall: 120/120 realistic

| class | realistic | sampled |
|---|---|---|
| amendment | 18 | 18 |
| cancellation | 10 | 10 |
| inquiry | 12 | 12 |
| new_order | 72 | 72 |
| other | 8 | 8 |

## Per-stratum realism

| stratum | sampled | unrealistic |
|---|---|---|
| new_order/flag:missing_po | 11 | 0 |
| new_order/flag:missing_quantity | 11 | 0 |
| new_order/flag:ambiguous_site | 9 | 0 |
| new_order/flag:discontinued_item | 9 | 0 |
| new_order/flag:qty_below_moq | 7 | 0 |
| new_order/flag:qty_above_max | 9 | 0 |
| new_order/flag:pack_size_trap | 7 | 0 |
| new_order/flag:mention_typo | 6 | 0 |
| new_order/flag:unsigned | 13 | 0 |
| new_order/flag:prices_stated | 28 | 0 |
| new_order/flag:price_mismatch | 8 | 0 |
| new_order/route:touchless | 22 | 0 |
| new_order/route:clarification | 12 | 0 |
| new_order/route:exception | 38 | 0 |
| new_order/layout:dash_list | 24 | 0 |
| new_order/layout:x_list | 17 | 0 |
| new_order/layout:reverse_list | 21 | 0 |
| new_order/layout:prose | 10 | 0 |
| new_order/po_placement:subject_only | 15 | 0 |
| new_order/po_placement:body_only | 15 | 0 |
| new_order/po_placement:both | 10 | 0 |
| new_order/quirk_a:canonical_unit | 42 | 0 |
| new_order/quirk_b:item_note | 20 | 0 |
| new_order/quirk_c:unsigned_personal | 12 | 0 |
| amendment/change:qty_change | 4 | 0 |
| amendment/change:add_item | 6 | 0 |
| amendment/change:remove_item | 4 | 0 |
| amendment/change:date_change | 4 | 0 |
| amendment/ref:po | 9 | 0 |
| amendment/ref:temporal | 9 | 0 |
| cancellation/ref:po | 4 | 0 |
| cancellation/ref:temporal | 6 | 0 |
| inquiry/type:quote_request | 4 | 0 |
| inquiry/type:stock_check | 4 | 0 |
| inquiry/type:general | 4 | 0 |
| other/type:vendor_marketing | 3 | 0 |
| other/type:misdirected | 2 | 0 |
| other/type:courier_notice | 3 | 0 |

## Note tags

| tag | qualifier | count |
|---|---|---|
| quirk:a | fine | 47 |
| quirk:b | fine | 20 |
| quirk:c | fine | 14 |
| quirk:d | fine | 6 |

## Protocol flags

- TST-SCN-000135: quirk:a fine; quirk:b fine (same-spec note); oracle verified above_max (laser labels 510 > max 500); protocol: bare '510 laser labels' is humanly ambiguous (labels vs packs) - spec's canonical-unit default reads packs; trap intended
- TST-SCN-000442: oracle verified unresolvable_unit ('buckles' not a unit token); protocol: unit-vs-product split of '1000 buckles strap clips' is convention-dependent - gold's parse (qty 1000 / unit 'buckles' / product 'strap clips') follows mention grammar consistently

## Unrealistic records — evidence dossier

## Adjudication

Ledger adjudication lives in docs/corpus_notes.md (quirk ledger, plus the
oracle-conventions section); the colour-note fix and its blast radius are
recorded as refreeze #1 in docs/frozen_test_fixlog.md.
