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

- overall: 113/120 realistic

| class | realistic | sampled |
|---|---|---|
| amendment | 18 | 18 |
| cancellation | 10 | 10 |
| inquiry | 12 | 12 |
| new_order | 65 | 72 |
| other | 8 | 8 |

## Per-stratum realism

| stratum | sampled | unrealistic |
|---|---|---|
| new_order/flag:missing_po | 11 | 0 |
| new_order/flag:missing_quantity | 11 | 2 |
| new_order/flag:ambiguous_site | 9 | 2 |
| new_order/flag:discontinued_item | 9 | 3 |
| new_order/flag:qty_below_moq | 7 | 0 |
| new_order/flag:qty_above_max | 9 | 0 |
| new_order/flag:pack_size_trap | 7 | 1 |
| new_order/flag:mention_typo | 6 | 0 |
| new_order/flag:unsigned | 13 | 1 |
| new_order/flag:prices_stated | 28 | 3 |
| new_order/flag:price_mismatch | 8 | 0 |
| new_order/route:touchless | 22 | 1 |
| new_order/route:clarification | 12 | 2 |
| new_order/route:exception | 38 | 4 |
| new_order/layout:dash_list | 24 | 1 |
| new_order/layout:x_list | 17 | 2 |
| new_order/layout:reverse_list | 21 | 4 |
| new_order/layout:prose | 10 | 0 |
| new_order/po_placement:subject_only | 15 | 3 |
| new_order/po_placement:body_only | 15 | 0 |
| new_order/po_placement:both | 10 | 3 |
| new_order/quirk_a:canonical_unit | 42 | 4 |
| new_order/quirk_b:item_note | 20 | 7 |
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
| quirk:b | fine | 11 |
| quirk:b | jarring | 7 |
| quirk:b | odd | 4 |
| quirk:c | fine | 13 |
| quirk:c | fine) | 1 |
| quirk:d | fine | 6 |

## Protocol flags

- TST-SCN-000135: quirk:a fine; quirk:b fine (same-spec note); oracle verified above_max (laser labels 510 > max 500); protocol: bare '510 laser labels' is humanly ambiguous (labels vs packs) - spec's canonical-unit default reads packs; trap intended
- TST-SCN-000442: oracle verified unresolvable_unit ('buckles' not a unit token); protocol: unit-vs-product split of '1000 buckles strap clips' is convention-dependent - gold's parse (qty 1000 / unit 'buckles' / product 'strap clips') follows mention grammar consistently

## Unrealistic records — evidence dossier

### TST-SCN-000004

- notes: quirk:a fine (16 roll/32 rl); quirk:b jarring - 'brown is fine if clear is out' on medium shipping box, no clear variant exists; gold verbatim; oracle verified (steel strapping discontinued; Orbit multi-site + no address -> delivery_site ask)
- layout=reverse_list · po_placement=both
- flags: ambiguous_site, discontinued_item
- item: 16 roll × Steel Strapping 19mm x 300m (style=canonical)
- item: 4 cartons × Padded Mailer 215x280mm Carton of 100 (style=alias)
- item: 200 each × medium shipping box (style=canonical)
- item: 32 rl × Machine Stretch Film 500mm x 1500m (style=alias)

Subject: PO OC-0019-5 – Orbit Components

```text
Hi,

PO for this order: OC-0019-5.

Please supply:

- Steel Strapping 19mm x 300m – 16 roll
- Padded Mailer 215x280mm Carton of 100 – 4 cartons
- medium shipping box – 200 each (brown is fine if clear is out)
- Machine Stretch Film 500mm x 1500m – 32 rl

Timing: 3 May.

Regards,
Alan
```

### TST-SCN-000072

- notes: quirk:b jarring - 'brown is fine if clear is out' on heavy duty carton, no clear variant; gold verbatim incl. '(usual unit, qty to follow)' -> unit_text 'unit' + qty null; oracle verified clarification/quantity
- layout=x_list · po_placement=subject_only
- flags: missing_quantity
- item: 150 — × large shipping box (style=none)
- item: — unit × heavy duty carton (style=alias)

Subject: Cairnwell Pharma Distribution – PO MPO/7686

```text
Hello,

Could you please arrange the following for us:

150 x large shipping box
heavy duty carton (usual unit, qty to follow) (brown is fine if clear is out)

Delivery in 5 days would suit us.

Kind regards,
Elaine
```

### TST-SCN-000095

- notes: quirk:b jarring - 'brown is fine if clear is out' on hardwood pallet; same-spec note fine; buyer null correct (shared mailbox, 'Purchasing team' closer); pack_size_trap '500 mailers' correct; oracle verified (unresolvable_unit + delivery_site)
- layout=reverse_list · po_placement=subject_only
- flags: ambiguous_site, pack_size_trap, unsigned
- item: 100 — × PAL-STD-601 (style=none)
- item: 500 mailers × poly mailers (style=piece, trap(packs=1))
- item: 1 pks × Strapping Buckles 12mm Bag of 1000 (style=alias)

Subject: Harbourline Logistics Pty Ltd – PO PO-48753

```text
Good morning,

We would like to place the following order:

- PAL-STD-601 – 100 (brown is fine if clear is out)
- poly mailers – 500 mailers
- Strapping Buckles 12mm Bag of 1000 – 1 pks (same spec as our last order)

Timing: 20 June.

Kind regards,
Purchasing team
```

### TST-SCN-000120

- notes: quirk:a fine (40 rl / 4 roll / 1 packs); quirk:b jarring - 'brown is fine if clear is out' on corner protectors, no clear variant; oracle verified (metal strapping discontinued; all three prices match)
- layout=dash_list · po_placement=both
- flags: discontinued_item, prices_stated
- item: 40 rl × shipping labels (style=alias, price=$18.50)
- item: 4 roll × metal strapping (style=canonical, price=$115.00)
- item: 1 packs × corner protectors (style=alias, price=$68.00)

Subject: PO MPO/7840 – Cairnwell Pharma Distribution

```text
Hello,

Could you please arrange the following for us:

- 40 rl shipping labels @ $18.50
- 4 roll metal strapping @ $115.00
- 1 packs corner protectors at $68.00 (brown is fine if clear is out)

We would need these ASAP.
Ship to: Unit 2, 41 Navigator Place, Eagle Farm QLD 4009.
Please book this against MPO/7840.

Kind regards,
Elaine
```

### TST-SCN-000310

- notes: quirk:a fine (half a dozen pack); quirk:b jarring - 'brown is fine if clear is out' on strapping buckles, no colour variants; oracle verified clarification/quantity (both stated prices match catalog)
- layout=reverse_list · po_placement=None
- flags: missing_quantity, prices_stated
- item: half a dozen pack × Strapping Buckles 12mm Bag of 1000 (style=canonical, price=$22.00)
- item: — — × large shipping box (style=none, price=$2.10)

Subject: New order – SwiftShip eCommerce

```text
Hey,

Can we get the following sorted please:

- Strapping Buckles 12mm Bag of 1000 – half a dozen pack at $22.00 (brown is fine if clear is out)
- large shipping box (qty to confirm) @ $2.10

Timing: 2 April.

Cheers,
Priya
```

### TST-SCN-000400

- notes: quirk:b jarring - 'brown is fine if clear is out' on nitrile gloves, no brown/clear variant; gold transcribes the note faithfully (label correct per calibration); oracle verified touchless ($11.50 matches; 30 ctns within 5..500)
- layout=x_list · po_placement=both
- flags: prices_stated
- item: 30 ctns × GLV-NTR-901 (style=alias, price=$11.50)

Subject: Purchase order PO-69669

```text
Hello,

Our PO: PO-69669.

We would like to place the following order:

30 ctns GLV-NTR-901 @ $11.50 (brown is fine if clear is out)

Delivery 15 March would suit us.
Ship to: Botany warehouse.

Kind regards,
Dana
```

### TST-SCN-000665

- notes: quirk:a fine (12 roll / 30 ea); quirk:b jarring - 'brown is fine if clear is out' on euro pallet, nonsensical for pallets; gold transcribes faithfully (label fine); oracle verified discontinued (steel strapping); no timing -> date null correct
- layout=reverse_list · po_placement=subject_only
- flags: discontinued_item
- item: 4 — × strapping (style=none)
- item: 50 — × Address Labels 99x38mm Sheet Pack of 100 (style=none)
- item: 30 ea × PAL-EUR-602 (style=alias)
- item: 12 roll × Steel Strapping 19mm x 300m (style=canonical)
- item: 80 pcs × heavy duty carton (style=alias)

Subject: Redgum Furniture Co – PO 4561737163

```text
Hi,

Order as follows:

- strapping – 4
- Address Labels 99x38mm Sheet Pack of 100 – 50
- PAL-EUR-602 – 30 ea (brown is fine if clear is out)
- Steel Strapping 19mm x 300m – 12 roll
- heavy duty carton – 80 pcs

Regards,
Marcus
```

## Adjudication

Pending — step 1.8b2 fills this section after per-record adjudication and
the fix-vs-record decision. This is the cheap refreeze window (no baseline
numbers exist yet); see docs/frozen_test_fixlog.md for the ritual.
