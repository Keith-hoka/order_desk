# Audit sheet — frozen test subsample (step 1.8)

Fill data/audit/verdicts.jsonl in place: one JSON line per record, same
order as this sheet. Set the two booleans, add notes where useful. Do not
reorder or delete lines; multiple sittings are fine.

- **realistic** — read as an ops person at a packaging supplier: could this
  email land in your inbox without feeling machine-written? Judge the quirk
  ledger from docs/corpus_notes.md here and tag notes accordingly
  (`quirk:a jarring`, `quirk:b fine`). Ledger shorthand: (a) singular
  canonical units ("20 roll of"); (b) item notes mismatched to the product;
  (c) unsigned personal-mailbox emails ending at a bare sign-off; (d) the
  (a) family inside amendment glue.
- **labels_correct** — is everything we claim true? Class label; every
  gold_extraction field verbatim-correct including nulls (null means the
  email does not state it — an empty string or paraphrase is a fail); for
  new_order, the oracle line (route / asks / violations) per SPEC §1. For
  cancellation / inquiry / other there is no gold: judge the class label
  and, for cancellation, the referenced PO or temporal phrase.
- **Audit, do not fix.** Defects are findings recorded in verdicts; fixes go
  through the fixlog/refreeze ritual in step 1.8b, never by editing frozen
  files.

The `focus:` line under a record names the strata it was sampled to cover —
check those aspects with extra care, then judge the record as a whole.

---
### 001 · TST-SCN-000004 · new_order

From: alan.kwok@orbitcomponents.com.au    Sent: 2026-04-25T14:10:00+10:00
Subject: PO OC-0019-5 – Orbit Components

```text
Hi,

PO for this order: OC-0019-5.

Please supply:

- Steel Strapping 19mm x 300m – 16 roll
- Padded Mailer 215x280mm Carton of 100 – 4 cartons
- medium shipping box – 200 each (no substitutions please)
- Machine Stretch Film 500mm x 1500m – 32 rl

Timing: 3 May.

Regards,
Alan
```

gold_extraction:
```json
{
  "buyer_name_text": "Alan",
  "customer_po_text": "OC-0019-5",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Steel Strapping 19mm x 300m",
      "quantity": 16,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "Padded Mailer 215x280mm Carton of 100",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "cartons"
    },
    {
      "item_notes": "no substitutions please",
      "product_text": "medium shipping box",
      "quantity": 200,
      "unit_price_text": null,
      "unit_text": "each"
    },
    {
      "item_notes": null,
      "product_text": "Machine Stretch Film 500mm x 1500m",
      "quantity": 32,
      "unit_price_text": null,
      "unit_text": "rl"
    }
  ],
  "notes": null,
  "requested_date_text": "3 May"
}
```

oracle: route=exception  asks=['delivery_site']  violations=['discontinued']
focus: flag:ambiguous_site, flag:discontinued_item, route:exception, layout:reverse_list, po_placement:both, quirk_a:canonical_unit, quirk_b:item_note

### 002 · TST-SCN-000005 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-02-04T17:11:00+11:00
Subject: Order request – Redgum Furniture Co

```text
Please supply:

- bubble mailers – 300 mailers

We would need these as soon as you can.
Delivery address: Dandenong plant.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": null,
  "delivery_address_text": "Dandenong plant",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "bubble mailers",
      "quantity": 300,
      "unit_price_text": null,
      "unit_text": "mailers"
    }
  ],
  "notes": null,
  "requested_date_text": "as soon as you can"
}
```

oracle: route=exception  asks=[]  violations=['unresolvable_unit']
focus: flag:missing_po, flag:pack_size_trap, route:exception, layout:reverse_list

### 003 · TST-SCN-000010 · new_order

From: sam.oneill@metroprint.com.au    Sent: 2026-03-27T12:22:00+11:00
Subject: Restock for Metro Print Group

```text
Good morning,

Our PO: MPG-270618.

We would like to place the following order:

- Steel Strapping 19mm x 300m – 16
- Clear Packing Tape 48mm x 75m – 72

Kind regards,
Sam
```

gold_extraction:
```json
{
  "buyer_name_text": "Sam",
  "customer_po_text": "MPG-270618",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Steel Strapping 19mm x 300m",
      "quantity": 16,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Clear Packing Tape 48mm x 75m",
      "quantity": 72,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=exception  asks=[]  violations=['discontinued']
focus: flag:discontinued_item, route:exception, layout:reverse_list, po_placement:body_only

### 004 · TST-SCN-000013 · new_order

From: sofia@bightandbay.com.au    Sent: 2026-05-22T10:09:00+10:00
Subject: Supplies order

```text
Order as follows:

- a dozen roll thermal labels @ $18.50
- 9 unit hd carton at $3.85
- 10 case disposable gloves at $11.50
- 2 pack Strapping Buckles 12mm Bag of 1000 at $22.00

Delivery 31 May would suit us.
Ship to: Port Adelaide depot.
Please note: site induction required for drivers.

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": "Port Adelaide depot",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "thermal labels",
      "quantity": 12,
      "unit_price_text": "$18.50",
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "hd carton",
      "quantity": 9,
      "unit_price_text": "$3.85",
      "unit_text": "unit"
    },
    {
      "item_notes": null,
      "product_text": "disposable gloves",
      "quantity": 10,
      "unit_price_text": "$11.50",
      "unit_text": "case"
    },
    {
      "item_notes": null,
      "product_text": "Strapping Buckles 12mm Bag of 1000",
      "quantity": 2,
      "unit_price_text": "$22.00",
      "unit_text": "pack"
    }
  ],
  "notes": "site induction required for drivers",
  "requested_date_text": "31 May"
}
```

oracle: route=exception  asks=[]  violations=['below_moq']
focus: flag:qty_below_moq, flag:prices_stated, route:exception, layout:dash_list, quirk_a:canonical_unit

### 005 · TST-SCN-000017 · new_order

From: tom.barker@swiftshipgroup.com    Sent: 2026-05-13T08:04:00+10:00
Subject: Restock for SwiftShip eCommerce

```text
Hi,

Can we get the following sorted please:

- 50 gloves

Delivery in 3 days would suit us.
Delivery address: Alexandria fulfilment centre.

Cheers,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": null,
  "delivery_address_text": "Alexandria fulfilment centre",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "gloves",
      "quantity": 50,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "in 3 days"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:unsigned, route:touchless, layout:dash_list, quirk_c:unsigned_personal

### 006 · TST-SCN-000020 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-03-13T17:39:00+11:00
Subject: Supplies order

```text
Please supply:

8 rl Bubble Wrap Roll 500mm x 100m 10mm Bubble
4 carton Poly Mailer 310x405mm Carton of 500

Timing: 25 March.
Please note: call before delivery.
PO for this order: 4525751839.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4525751839",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Bubble Wrap Roll 500mm x 100m 10mm Bubble",
      "quantity": 8,
      "unit_price_text": null,
      "unit_text": "rl"
    },
    {
      "item_notes": null,
      "product_text": "Poly Mailer 310x405mm Carton of 500",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "carton"
    }
  ],
  "notes": "call before delivery",
  "requested_date_text": "25 March"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:x_list, po_placement:body_only, quirk_a:canonical_unit

### 007 · TST-SCN-000021 · new_order

From: orders@harbourline.com.au    Sent: 2026-04-11T15:56:00+10:00
Subject: Supplies order

```text
Hello,

We would like to order 500 mailers of plastic mailers and 16 Poly Strapping 12mm x 1000m.

Delivery 23 April would suit us.
Our PO: PO-06903.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": "PO-06903",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "plastic mailers",
      "quantity": 500,
      "unit_price_text": null,
      "unit_text": "mailers"
    },
    {
      "item_notes": null,
      "product_text": "Poly Strapping 12mm x 1000m",
      "quantity": 16,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "23 April"
}
```

oracle: route=exception  asks=['delivery_site']  violations=['unresolvable_unit']
focus: flag:ambiguous_site, flag:pack_size_trap, route:exception, layout:prose, po_placement:body_only

### 008 · TST-SCN-000051 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-03-04T12:46:00+11:00
Subject: Order request – Redgum Furniture Co

```text
Hi,

Our PO: 4502564833.

Please send 12 rl of bubble roll at $42.00.

Timing: 9 March.
Ship to: 16 Assembly Drive, Dandenong South VIC 3175.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4502564833",
  "delivery_address_text": "16 Assembly Drive, Dandenong South VIC 3175",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "bubble roll",
      "quantity": 12,
      "unit_price_text": "$42.00",
      "unit_text": "rl"
    }
  ],
  "notes": null,
  "requested_date_text": "9 March"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:prices_stated, route:touchless, layout:prose, po_placement:body_only

### 009 · TST-SCN-000058 · new_order

From: dana.whitfield@harbourline.com.au    Sent: 2026-03-03T09:53:00+11:00
Subject: Restock for Harbourline Logistics Pty Ltd

```text
Good morning,

We would like to place the following order:

- 4 rl STR-STL-703
- 250 each Large Shipping Carton 500x400x350mm

Delivery in 3 days would suit us.
Please note: deliver to rear dock.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "STR-STL-703",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "rl"
    },
    {
      "item_notes": null,
      "product_text": "Large Shipping Carton 500x400x350mm",
      "quantity": 250,
      "unit_price_text": null,
      "unit_text": "each"
    }
  ],
  "notes": "deliver to rear dock",
  "requested_date_text": "in 3 days"
}
```

oracle: route=exception  asks=['delivery_site']  violations=['discontinued']
focus: flag:missing_po, flag:ambiguous_site, flag:discontinued_item, route:exception, layout:dash_list, quirk_a:canonical_unit

### 010 · TST-SCN-000070 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-06-06T09:03:00+10:00
Subject: Supplies order

```text
Hi,

Please book this against 4521056641.

Please supply:

288 rolls TPE-FRG-203 at $3.10

We would need these when you can.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4521056641",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "TPE-FRG-203",
      "quantity": 288,
      "unit_price_text": "$3.10",
      "unit_text": "rolls"
    }
  ],
  "notes": null,
  "requested_date_text": "when you can"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:prices_stated, route:touchless, layout:x_list, po_placement:body_only

### 011 · TST-SCN-000072 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-05-05T17:25:00+10:00
Subject: Cairnwell Pharma Distribution – PO MPO/7686

```text
Hello,

Could you please arrange the following for us:

150 x large shipping box
heavy duty carton (usual unit, qty to follow) (no substitutions please)

Delivery in 5 days would suit us.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/7686",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "large shipping box",
      "quantity": 150,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": "no substitutions please",
      "product_text": "heavy duty carton",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": "unit"
    }
  ],
  "notes": null,
  "requested_date_text": "in 5 days"
}
```

oracle: route=clarification  asks=['quantity']  violations=[]
focus: flag:missing_quantity, route:clarification, layout:x_list, po_placement:subject_only, quirk_b:item_note

### 012 · TST-SCN-000085 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-05-25T16:48:00+10:00
Subject: New order – Cairnwell Pharma Distribution

```text
Hello,

Could you please arrange the following for us:

half a dozen x buckles at $19.80
108 x pakcaging tape @ $2.40

We would need these in 5 days.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "buckles",
      "quantity": 6,
      "unit_price_text": "$19.80",
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "pakcaging tape",
      "quantity": 108,
      "unit_price_text": "$2.40",
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "in 5 days"
}
```

oracle: route=exception  asks=[]  violations=['price_mismatch', 'unresolvable_product']
focus: flag:missing_po, flag:mention_typo, flag:prices_stated, flag:price_mismatch, route:exception, layout:x_list

### 013 · TST-SCN-000095 · new_order

From: orders@harbourline.com.au    Sent: 2026-06-12T12:46:00+10:00
Subject: Harbourline Logistics Pty Ltd – PO PO-48753

```text
Good morning,

We would like to place the following order:

- PAL-STD-601 – 100 (no substitutions please)
- poly mailers – 500 mailers
- Strapping Buckles 12mm Bag of 1000 – 1 pks (same spec as our last order)

Timing: 20 June.

Kind regards,
Purchasing team
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": "PO-48753",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": "no substitutions please",
      "product_text": "PAL-STD-601",
      "quantity": 100,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "poly mailers",
      "quantity": 500,
      "unit_price_text": null,
      "unit_text": "mailers"
    },
    {
      "item_notes": "same spec as our last order",
      "product_text": "Strapping Buckles 12mm Bag of 1000",
      "quantity": 1,
      "unit_price_text": null,
      "unit_text": "pks"
    }
  ],
  "notes": null,
  "requested_date_text": "20 June"
}
```

oracle: route=exception  asks=['delivery_site']  violations=['unresolvable_unit']
focus: flag:ambiguous_site, flag:pack_size_trap, flag:unsigned, route:exception, layout:reverse_list, po_placement:subject_only, quirk_b:item_note

### 014 · TST-SCN-000097 · new_order

From: orders@harbourline.com.au    Sent: 2026-03-11T10:30:00+11:00
Subject: PO PO-52471 – Harbourline Logistics Pty Ltd

```text
Good morning,

Please book this against PO-52471.

Could you please send us 8 rls of LBL-4X6-301 @ $18.50 and half a dozen rls of Steel Strapping 19mm x 300m at $115.00.

Timing: in 5 days.
Deliver to Botany warehouse.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": "PO-52471",
  "delivery_address_text": "Botany warehouse",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "LBL-4X6-301",
      "quantity": 8,
      "unit_price_text": "$18.50",
      "unit_text": "rls"
    },
    {
      "item_notes": null,
      "product_text": "Steel Strapping 19mm x 300m",
      "quantity": 6,
      "unit_price_text": "$115.00",
      "unit_text": "rls"
    }
  ],
  "notes": null,
  "requested_date_text": "in 5 days"
}
```

oracle: route=exception  asks=[]  violations=['discontinued']
focus: flag:discontinued_item, flag:prices_stated, route:exception, layout:prose, po_placement:both

### 015 · TST-SCN-000110 · new_order

From: purchasing@orbitcomponents.com.au    Sent: 2026-01-08T15:25:00+11:00
Subject: New order – Orbit Components

```text
Order as follows:

- Edge Protectors 50x50x1200mm Bundle of 50 (usual bag, qty to follow)
- heavy duty box – 20 each

We would need these 14 January.
Delivery address: 14 Egerton Street, Silverwater NSW 2128.
PO for this order: OC-4383-7.

Regards,
Alan
```

gold_extraction:
```json
{
  "buyer_name_text": "Alan",
  "customer_po_text": "OC-4383-7",
  "delivery_address_text": "14 Egerton Street, Silverwater NSW 2128",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Edge Protectors 50x50x1200mm Bundle of 50",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": "bag"
    },
    {
      "item_notes": null,
      "product_text": "heavy duty box",
      "quantity": 20,
      "unit_price_text": null,
      "unit_text": "each"
    }
  ],
  "notes": null,
  "requested_date_text": "14 January"
}
```

oracle: route=clarification  asks=['quantity']  violations=[]
focus: flag:missing_quantity, route:clarification, layout:reverse_list, po_placement:body_only, quirk_a:canonical_unit

### 016 · TST-SCN-000120 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-05-30T17:53:00+10:00
Subject: PO MPO/7840 – Cairnwell Pharma Distribution

```text
Hello,

Could you please arrange the following for us:

- 40 rl shipping labels @ $18.50
- 4 roll metal strapping @ $115.00
- 1 packs corner protectors at $68.00 (no substitutions please)

We would need these ASAP.
Ship to: Unit 2, 41 Navigator Place, Eagle Farm QLD 4009.
Please book this against MPO/7840.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/7840",
  "delivery_address_text": "Unit 2, 41 Navigator Place, Eagle Farm QLD 4009",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "shipping labels",
      "quantity": 40,
      "unit_price_text": "$18.50",
      "unit_text": "rl"
    },
    {
      "item_notes": null,
      "product_text": "metal strapping",
      "quantity": 4,
      "unit_price_text": "$115.00",
      "unit_text": "roll"
    },
    {
      "item_notes": "no substitutions please",
      "product_text": "corner protectors",
      "quantity": 1,
      "unit_price_text": "$68.00",
      "unit_text": "packs"
    }
  ],
  "notes": null,
  "requested_date_text": "ASAP"
}
```

oracle: route=exception  asks=[]  violations=['discontinued']
focus: flag:discontinued_item, flag:prices_stated, route:exception, layout:dash_list, po_placement:both, quirk_a:canonical_unit, quirk_b:item_note

### 017 · TST-SCN-000128 · new_order

From: josh@fernvalenurseries.com.au    Sent: 2026-06-09T11:11:00+10:00
Subject: Restock for Fernvale Nurseries

```text
Hi,

Can we get the following sorted please:

- buckles – 10 pack @ $22.00
- STR-PLY-701 – 20 rls at $49.00
- edge protectors – 2 bags at $68.00
- warning tape – 360 @ $3.10

Timing: when you can.
Ship to: 210 Banks Creek Road, Fernvale QLD 4306.
Please note: tailgate required.

Cheers,
Josh
```

gold_extraction:
```json
{
  "buyer_name_text": "Josh",
  "customer_po_text": null,
  "delivery_address_text": "210 Banks Creek Road, Fernvale QLD 4306",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "buckles",
      "quantity": 10,
      "unit_price_text": "$22.00",
      "unit_text": "pack"
    },
    {
      "item_notes": null,
      "product_text": "STR-PLY-701",
      "quantity": 20,
      "unit_price_text": "$49.00",
      "unit_text": "rls"
    },
    {
      "item_notes": null,
      "product_text": "edge protectors",
      "quantity": 2,
      "unit_price_text": "$68.00",
      "unit_text": "bags"
    },
    {
      "item_notes": null,
      "product_text": "warning tape",
      "quantity": 360,
      "unit_price_text": "$3.10",
      "unit_text": null
    }
  ],
  "notes": "tailgate required",
  "requested_date_text": "when you can"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:prices_stated, route:touchless, layout:reverse_list, quirk_a:canonical_unit

### 018 · TST-SCN-000135 · new_order

From: josh@fernvalenurseries.com.au    Sent: 2026-05-31T09:13:00+10:00
Subject: Supplies order

```text
Morning,

Hoping to get another order in:

- 510 laser labels @ $14.50 (same spec as our last order)
- 8 carton courier satchels @ $55.00

Timing: as soon as you can.
Ship to: 210 Banks Creek Road, Fernvale QLD 4306.

Cheers,
Josh
```

gold_extraction:
```json
{
  "buyer_name_text": "Josh",
  "customer_po_text": null,
  "delivery_address_text": "210 Banks Creek Road, Fernvale QLD 4306",
  "line_items": [
    {
      "item_notes": "same spec as our last order",
      "product_text": "laser labels",
      "quantity": 510,
      "unit_price_text": "$14.50",
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "courier satchels",
      "quantity": 8,
      "unit_price_text": "$55.00",
      "unit_text": "carton"
    }
  ],
  "notes": null,
  "requested_date_text": "as soon as you can"
}
```

oracle: route=exception  asks=[]  violations=['above_max']
focus: flag:qty_above_max, flag:prices_stated, route:exception, layout:dash_list, quirk_a:canonical_unit, quirk_b:item_note

### 019 · TST-SCN-000145 · new_order

From: dana.whitfield@harbourline.com.au    Sent: 2026-01-10T13:04:00+11:00
Subject: New order – Harbourline Logistics Pty Ltd

```text
Hello,

We would like to place the following order:

- 5 bag Address Labels 99x38mm Sheet Pack of 100 at $14.50

We would need these 13 January.
Deliver to Eastern Creek DC.
Our PO: PO-77214.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": "PO-77214",
  "delivery_address_text": "Eastern Creek DC",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Address Labels 99x38mm Sheet Pack of 100",
      "quantity": 5,
      "unit_price_text": "$14.50",
      "unit_text": "bag"
    }
  ],
  "notes": null,
  "requested_date_text": "13 January"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:prices_stated, route:touchless, layout:dash_list, po_placement:body_only

### 020 · TST-SCN-000166 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-05-20T15:07:00+10:00
Subject: Redgum Furniture Co – PO 4590772610

```text
Order as follows:

- a dozen roll Hand Stretch Film 500mm x 400m Clear at $8.58

Timing: 31 May.
Ship to: Dandenong plant.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4590772610",
  "delivery_address_text": "Dandenong plant",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Hand Stretch Film 500mm x 400m Clear",
      "quantity": 12,
      "unit_price_text": "$8.58",
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": "31 May"
}
```

oracle: route=exception  asks=[]  violations=['price_mismatch']
focus: flag:prices_stated, flag:price_mismatch, route:exception, layout:dash_list, po_placement:subject_only, quirk_a:canonical_unit

### 021 · TST-SCN-000168 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-03-20T16:38:00+11:00
Subject: PO MPO/6209 – Cairnwell Pharma Distribution

```text
Hello,

We would like to place the following order:

- 25 each large shipping box @ $2.10
- 50 pack laser labels at $14.50
- 24 roll machine wrap at $60.80
- 3 cartons Poly Mailer 310x405mm Carton of 500 @ $55.00
- 8 roll shipping labels at $18.50 (same spec as our last order)

Delivery 2 April would suit us.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/6209",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "large shipping box",
      "quantity": 25,
      "unit_price_text": "$2.10",
      "unit_text": "each"
    },
    {
      "item_notes": null,
      "product_text": "laser labels",
      "quantity": 50,
      "unit_price_text": "$14.50",
      "unit_text": "pack"
    },
    {
      "item_notes": null,
      "product_text": "machine wrap",
      "quantity": 24,
      "unit_price_text": "$60.80",
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "Poly Mailer 310x405mm Carton of 500",
      "quantity": 3,
      "unit_price_text": "$55.00",
      "unit_text": "cartons"
    },
    {
      "item_notes": "same spec as our last order",
      "product_text": "shipping labels",
      "quantity": 8,
      "unit_price_text": "$18.50",
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": "2 April"
}
```

oracle: route=exception  asks=[]  violations=['price_mismatch']
focus: flag:prices_stated, flag:price_mismatch, route:exception, layout:dash_list, po_placement:subject_only, quirk_a:canonical_unit, quirk_b:item_note

### 022 · TST-SCN-000178 · new_order

From: helen.diaz@metroprint.com.au    Sent: 2026-04-04T11:23:00+11:00
Subject: Supplies order

```text
Hello,

Could you please arrange the following for us:

- laser labels – 200 labels

Timing: as soon as you can.
Ship to: 55 Fabrication Way, Sunshine West VIC 3020.
Just a heads up: deliver to rear dock.

Kind regards,
Helen
```

gold_extraction:
```json
{
  "buyer_name_text": "Helen",
  "customer_po_text": null,
  "delivery_address_text": "55 Fabrication Way, Sunshine West VIC 3020",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "laser labels",
      "quantity": 200,
      "unit_price_text": null,
      "unit_text": "labels"
    }
  ],
  "notes": "deliver to rear dock",
  "requested_date_text": "as soon as you can"
}
```

oracle: route=exception  asks=[]  violations=['unresolvable_unit']
focus: flag:missing_po, flag:pack_size_trap, route:exception, layout:reverse_list

### 023 · TST-SCN-000181 · new_order

From: sofia@bightandbay.com.au    Sent: 2026-06-26T10:02:00+10:00
Subject: Restock for Bight & Bay Seafoods

```text
Hi,

Please supply:

- 250 each large shipping box

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "large shipping box",
      "quantity": 250,
      "unit_price_text": null,
      "unit_text": "each"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:dash_list, quirk_a:canonical_unit

### 024 · TST-SCN-000207 · new_order

From: priya@swiftship.au    Sent: 2026-02-15T11:31:00+11:00
Subject: Restock for SwiftShip eCommerce

```text
Hey,

Can you send over 250 unit of CTN-LG-003 at $2.10?

We would need these 26 February.
Please note: call before delivery.

Cheers,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "CTN-LG-003",
      "quantity": 250,
      "unit_price_text": "$2.10",
      "unit_text": "unit"
    }
  ],
  "notes": "call before delivery",
  "requested_date_text": "26 February"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:unsigned, flag:prices_stated, route:touchless, layout:prose, quirk_c:unsigned_personal

### 025 · TST-SCN-000208 · new_order

From: sam.oneill@metroprint.com.au    Sent: 2026-04-10T11:59:00+10:00
Subject: Metro Print Group – PO MPG-222844

```text
Good morning,

PO for this order: MPG-222844.

We would like to place the following order:

- thermal labels – 4 rls at $18.50
- TPE-CLR-201 – 36 rl @ $2.40
- STR-BKL-702 – 2 pack at $22.00
- kraft paper – 8 roll @ $52.00
- big bubble – 82 roll at $98.00

We would need these 13 April.
Deliver to Sunshine West plant.

Kind regards,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": "MPG-222844",
  "delivery_address_text": "Sunshine West plant",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "thermal labels",
      "quantity": 4,
      "unit_price_text": "$18.50",
      "unit_text": "rls"
    },
    {
      "item_notes": null,
      "product_text": "TPE-CLR-201",
      "quantity": 36,
      "unit_price_text": "$2.40",
      "unit_text": "rl"
    },
    {
      "item_notes": null,
      "product_text": "STR-BKL-702",
      "quantity": 2,
      "unit_price_text": "$22.00",
      "unit_text": "pack"
    },
    {
      "item_notes": null,
      "product_text": "kraft paper",
      "quantity": 8,
      "unit_price_text": "$52.00",
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "big bubble",
      "quantity": 82,
      "unit_price_text": "$98.00",
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": "13 April"
}
```

oracle: route=exception  asks=[]  violations=['above_max']
focus: flag:qty_above_max, flag:unsigned, flag:prices_stated, route:exception, layout:reverse_list, po_placement:both, quirk_a:canonical_unit, quirk_c:unsigned_personal

### 026 · TST-SCN-000212 · new_order

From: josh@fernvalenurseries.com.au    Sent: 2026-01-16T15:15:00+11:00
Subject: New order – Fernvale Nurseries

```text
Hey,

Hoping to get another order in:

- half a dozen boxes padded bags (must be the heavy duty ones)
- 100 pcs europallet
- 4 Edge Protectors 50x50x1200mm Bundle of 50
- 32 rl Machine Stretch Film 500mm x 1500m (no substitutions please)
- 29 Fragile Printed Tape 48mm x 66m

Cheers,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": "must be the heavy duty ones",
      "product_text": "padded bags",
      "quantity": 6,
      "unit_price_text": null,
      "unit_text": "boxes"
    },
    {
      "item_notes": null,
      "product_text": "europallet",
      "quantity": 100,
      "unit_price_text": null,
      "unit_text": "pcs"
    },
    {
      "item_notes": null,
      "product_text": "Edge Protectors 50x50x1200mm Bundle of 50",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": "no substitutions please",
      "product_text": "Machine Stretch Film 500mm x 1500m",
      "quantity": 32,
      "unit_price_text": null,
      "unit_text": "rl"
    },
    {
      "item_notes": null,
      "product_text": "Fragile Printed Tape 48mm x 66m",
      "quantity": 29,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=exception  asks=[]  violations=['below_moq']
focus: flag:qty_below_moq, flag:unsigned, route:exception, layout:dash_list, quirk_b:item_note, quirk_c:unsigned_personal

### 027 · TST-SCN-000219 · new_order

From: sofia@bightandbay.com.au    Sent: 2026-02-13T09:30:00+11:00
Subject: Restock for Bight & Bay Seafoods

```text
Order as follows:

- 20 bubble roll @ $42.00
- 4 pack Edge Protectors 50x50x1200mm Bundle of 50 at $68.00
- 25 each big box at $2.10
- 144 roll printed fragile tape @ $3.41 (same spec as our last order)

Timing: 16 February.

Thanks,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "bubble roll",
      "quantity": 20,
      "unit_price_text": "$42.00",
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Edge Protectors 50x50x1200mm Bundle of 50",
      "quantity": 4,
      "unit_price_text": "$68.00",
      "unit_text": "pack"
    },
    {
      "item_notes": null,
      "product_text": "big box",
      "quantity": 25,
      "unit_price_text": "$2.10",
      "unit_text": "each"
    },
    {
      "item_notes": "same spec as our last order",
      "product_text": "printed fragile tape",
      "quantity": 144,
      "unit_price_text": "$3.41",
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": "16 February"
}
```

oracle: route=exception  asks=[]  violations=['price_mismatch']
focus: flag:unsigned, flag:prices_stated, flag:price_mismatch, route:exception, layout:dash_list, quirk_a:canonical_unit, quirk_b:item_note, quirk_c:unsigned_personal

### 028 · TST-SCN-000226 · new_order

From: purchasing@orbitcomponents.com.au    Sent: 2026-06-11T07:45:00+10:00
Subject: Orbit Components – PO OC-4751-9

```text
Order as follows:

- MLR-PLY-502 – 4 carton
- void fill – 1 rls
- Nitrile Gloves Large Box of 100 – 15
- Machine Stretch Film 500mm x 1500m – two dozen roll
- Fragile Printed Tape 48mm x 66m – 36 roll

Delivery address: Warehouse 3, 40 Yato Road, Prestons NSW 2170.
Just a heads up: site induction required for drivers.

Regards,
Alan
```

gold_extraction:
```json
{
  "buyer_name_text": "Alan",
  "customer_po_text": "OC-4751-9",
  "delivery_address_text": "Warehouse 3, 40 Yato Road, Prestons NSW 2170",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "MLR-PLY-502",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "carton"
    },
    {
      "item_notes": null,
      "product_text": "void fill",
      "quantity": 1,
      "unit_price_text": null,
      "unit_text": "rls"
    },
    {
      "item_notes": null,
      "product_text": "Nitrile Gloves Large Box of 100",
      "quantity": 15,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Machine Stretch Film 500mm x 1500m",
      "quantity": 24,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "Fragile Printed Tape 48mm x 66m",
      "quantity": 36,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": "site induction required for drivers",
  "requested_date_text": null
}
```

oracle: route=exception  asks=[]  violations=['below_moq']
focus: flag:qty_below_moq, route:exception, layout:reverse_list, po_placement:subject_only, quirk_a:canonical_unit

### 029 · TST-SCN-000252 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-02-03T07:02:00+11:00
Subject: PO MPO/3666 – Cairnwell Pharma Distribution

```text
Hello,

We would like to place the following order:

- TPE-FRG-203 – 1476 rls
- packing paper (usual roll, qty to follow)
- padded bags – 100 mailers

Timing: in a fortnight.

Kind regards,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": "MPO/3666",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "TPE-FRG-203",
      "quantity": 1476,
      "unit_price_text": null,
      "unit_text": "rls"
    },
    {
      "item_notes": null,
      "product_text": "packing paper",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "padded bags",
      "quantity": 100,
      "unit_price_text": null,
      "unit_text": "mailers"
    }
  ],
  "notes": null,
  "requested_date_text": "in a fortnight"
}
```

oracle: route=exception  asks=['quantity']  violations=['above_max', 'unresolvable_unit']
focus: flag:missing_quantity, flag:qty_above_max, flag:pack_size_trap, flag:unsigned, route:exception, layout:reverse_list, po_placement:subject_only, quirk_a:canonical_unit, quirk_c:unsigned_personal

### 030 · TST-SCN-000259 · new_order

From: alan.kwok@orbitcomponents.com.au    Sent: 2026-02-02T08:48:00+11:00
Subject: PO OC-6940-7 – Orbit Components

```text
Please supply:

- 2196 rls Brown Packing Tape 48mm x 75m

Timing: 13 February.

Regards,
Alan
```

gold_extraction:
```json
{
  "buyer_name_text": "Alan",
  "customer_po_text": "OC-6940-7",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Brown Packing Tape 48mm x 75m",
      "quantity": 2196,
      "unit_price_text": null,
      "unit_text": "rls"
    }
  ],
  "notes": null,
  "requested_date_text": "13 February"
}
```

oracle: route=exception  asks=['delivery_site']  violations=['above_max']
focus: flag:ambiguous_site, flag:qty_above_max, route:exception, layout:dash_list, po_placement:subject_only

### 031 · TST-SCN-000266 · new_order

From: josh@fernvalenurseries.com.au    Sent: 2026-01-24T14:01:00+11:00
Subject: New order – Fernvale Nurseries

```text
Hi,

Hoping to get another order in:

- wide bubble wrap – 12 rls
- PAL-STD-601 – 100 each
- STR-PLY-701 – 20 roll (no substitutions please)

Delivery in a fortnight would suit us.
Just a heads up: site induction required for drivers.

Cheers,
Josh
```

gold_extraction:
```json
{
  "buyer_name_text": "Josh",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "wide bubble wrap",
      "quantity": 12,
      "unit_price_text": null,
      "unit_text": "rls"
    },
    {
      "item_notes": null,
      "product_text": "PAL-STD-601",
      "quantity": 100,
      "unit_price_text": null,
      "unit_text": "each"
    },
    {
      "item_notes": "no substitutions please",
      "product_text": "STR-PLY-701",
      "quantity": 20,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": "site induction required for drivers",
  "requested_date_text": "in a fortnight"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:reverse_list, quirk_a:canonical_unit, quirk_b:item_note

### 032 · TST-SCN-000290 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-04-28T16:12:00+10:00
Subject: PO MPO/7633 – Cairnwell Pharma Distribution

```text
Hello,

Could you please arrange the following for us:

- wide bubble wrap (qty to confirm)

We would need these 10 May.
Deliver to Unit 2, 41 Navigator Place, Eagle Farm QLD 4009.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/7633",
  "delivery_address_text": "Unit 2, 41 Navigator Place, Eagle Farm QLD 4009",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "wide bubble wrap",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "10 May"
}
```

oracle: route=clarification  asks=['quantity']  violations=[]
focus: flag:missing_quantity, route:clarification, layout:reverse_list, po_placement:subject_only

### 033 · TST-SCN-000303 · new_order

From: dana.whitfield@harbourline.com.au    Sent: 2026-07-04T08:08:00+10:00
Subject: New order – Harbourline Logistics Pty Ltd

```text
Hello,

We would like to place the following order:

- STR-BKL-702 – 4
- double wall box – 40
- PAL-EUR-602 – 60 each

Timing: in a week.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "STR-BKL-702",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "double wall box",
      "quantity": 40,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "PAL-EUR-602",
      "quantity": 60,
      "unit_price_text": null,
      "unit_text": "each"
    }
  ],
  "notes": null,
  "requested_date_text": "in a week"
}
```

oracle: route=clarification  asks=['delivery_site']  violations=[]
focus: flag:missing_po, flag:ambiguous_site, route:clarification, layout:reverse_list, quirk_a:canonical_unit

### 034 · TST-SCN-000310 · new_order

From: priya@swiftship.au    Sent: 2026-03-27T07:07:00+11:00
Subject: New order – SwiftShip eCommerce

```text
Hey,

Can we get the following sorted please:

- Strapping Buckles 12mm Bag of 1000 – half a dozen pack at $22.00 (no substitutions please)
- large shipping box (qty to confirm) @ $2.10

Timing: 2 April.

Cheers,
Priya
```

gold_extraction:
```json
{
  "buyer_name_text": "Priya",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": "no substitutions please",
      "product_text": "Strapping Buckles 12mm Bag of 1000",
      "quantity": 6,
      "unit_price_text": "$22.00",
      "unit_text": "pack"
    },
    {
      "item_notes": null,
      "product_text": "large shipping box",
      "quantity": null,
      "unit_price_text": "$2.10",
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "2 April"
}
```

oracle: route=clarification  asks=['quantity']  violations=[]
focus: flag:missing_quantity, flag:prices_stated, route:clarification, layout:reverse_list, quirk_a:canonical_unit, quirk_b:item_note

### 035 · TST-SCN-000357 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-05-07T09:22:00+10:00
Subject: Supplies order

```text
Good morning,

Could you please arrange the following for us:

100 boards corner boards
50 x nirtile gloves

Delivery when you can would suit us.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "corner boards",
      "quantity": 100,
      "unit_price_text": null,
      "unit_text": "boards"
    },
    {
      "item_notes": null,
      "product_text": "nirtile gloves",
      "quantity": 50,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "when you can"
}
```

oracle: route=exception  asks=[]  violations=['unresolvable_unit', 'unresolvable_product']
focus: flag:missing_po, flag:pack_size_trap, flag:mention_typo, route:exception, layout:x_list

### 036 · TST-SCN-000361 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-05-09T07:51:00+10:00
Subject: Redgum Furniture Co – PO 4507810708

```text
Please supply:

100 unit Euro Pallet 1200x800mm @ $36.00

We would need these ASAP.
Please book this against 4507810708.

Regards,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": "4507810708",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Euro Pallet 1200x800mm",
      "quantity": 100,
      "unit_price_text": "$36.00",
      "unit_text": "unit"
    }
  ],
  "notes": null,
  "requested_date_text": "ASAP"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:unsigned, flag:prices_stated, route:touchless, layout:x_list, po_placement:both, quirk_c:unsigned_personal

### 037 · TST-SCN-000381 · new_order

From: sofia@bightandbay.com.au    Sent: 2026-06-29T17:06:00+10:00
Subject: Order request – Bight & Bay Seafoods

```text
Hi,

Order as follows:

- 84 large bubble wrap
- 2 rl plastic strapping

Timing: in a week.
Ship to: 5 Jenkins Street, Port Adelaide SA 5015.

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": "5 Jenkins Street, Port Adelaide SA 5015",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "large bubble wrap",
      "quantity": 84,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "plastic strapping",
      "quantity": 2,
      "unit_price_text": null,
      "unit_text": "rl"
    }
  ],
  "notes": null,
  "requested_date_text": "in a week"
}
```

oracle: route=exception  asks=[]  violations=['above_max']
focus: flag:qty_above_max, route:exception, layout:dash_list

### 038 · TST-SCN-000394 · new_order

From: dana.whitfield@harbourline.com.au    Sent: 2026-04-09T10:59:00+10:00
Subject: Supplies order

```text
Hello,

We would like to place the following order:

- 360 sticky tape
- 75 piece Medium Shipping Carton 400x300x250mm
- half a dozen rl bubble roll

Delivery in 5 days would suit us.
PO for this order: PO-15378.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": "PO-15378",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "sticky tape",
      "quantity": 360,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Medium Shipping Carton 400x300x250mm",
      "quantity": 75,
      "unit_price_text": null,
      "unit_text": "piece"
    },
    {
      "item_notes": null,
      "product_text": "bubble roll",
      "quantity": 6,
      "unit_price_text": null,
      "unit_text": "rl"
    }
  ],
  "notes": null,
  "requested_date_text": "in 5 days"
}
```

oracle: route=clarification  asks=['delivery_site']  violations=[]
focus: flag:ambiguous_site, route:clarification, layout:dash_list, po_placement:body_only

### 039 · TST-SCN-000400 · new_order

From: orders@harbourline.com.au    Sent: 2026-03-10T11:35:00+11:00
Subject: Purchase order PO-69669

```text
Hello,

Our PO: PO-69669.

We would like to place the following order:

30 ctns GLV-NTR-901 @ $11.50 (no substitutions please)

Delivery 15 March would suit us.
Ship to: Botany warehouse.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": "PO-69669",
  "delivery_address_text": "Botany warehouse",
  "line_items": [
    {
      "item_notes": "no substitutions please",
      "product_text": "GLV-NTR-901",
      "quantity": 30,
      "unit_price_text": "$11.50",
      "unit_text": "ctns"
    }
  ],
  "notes": null,
  "requested_date_text": "15 March"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:prices_stated, route:touchless, layout:x_list, po_placement:both, quirk_b:item_note

### 040 · TST-SCN-000413 · new_order

From: alan.kwok@orbitcomponents.com.au    Sent: 2026-06-21T15:52:00+10:00
Subject: Purchase order OC-0316-4

```text
Hi,

Order as follows:

- 100 each Medium Shipping Carton 400x300x250mm
- 4 cartons padded bags
- 4 roll 4x6 labels
- 4 large bubble wrap
- tan tape (usual roll, qty to follow) (must be the heavy duty ones)

Timing: in 10 days.

Regards,
Alan
```

gold_extraction:
```json
{
  "buyer_name_text": "Alan",
  "customer_po_text": "OC-0316-4",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Medium Shipping Carton 400x300x250mm",
      "quantity": 100,
      "unit_price_text": null,
      "unit_text": "each"
    },
    {
      "item_notes": null,
      "product_text": "padded bags",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "cartons"
    },
    {
      "item_notes": null,
      "product_text": "4x6 labels",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "large bubble wrap",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": "must be the heavy duty ones",
      "product_text": "tan tape",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": "in 10 days"
}
```

oracle: route=clarification  asks=['quantity', 'delivery_site']  violations=[]
focus: flag:missing_quantity, flag:ambiguous_site, route:clarification, layout:dash_list, po_placement:subject_only, quirk_a:canonical_unit, quirk_b:item_note

### 041 · TST-SCN-000415 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-04-18T12:42:00+10:00
Subject: Order request – Cairnwell Pharma Distribution

```text
Hello,

PO for this order: MPO/5074.

We would like to place the following order:

20 x standard pallet at $27.20
60 pc Euro Pallet 1200x800mm @ $36.00

We would need these 29 April.
Please note: tailgate required.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/5074",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "standard pallet",
      "quantity": 20,
      "unit_price_text": "$27.20",
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Euro Pallet 1200x800mm",
      "quantity": 60,
      "unit_price_text": "$36.00",
      "unit_text": "pc"
    }
  ],
  "notes": "tailgate required",
  "requested_date_text": "29 April"
}
```

oracle: route=exception  asks=[]  violations=['price_mismatch']
focus: flag:prices_stated, flag:price_mismatch, route:exception, layout:x_list, po_placement:body_only

### 042 · TST-SCN-000422 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-05-29T13:22:00+10:00
Subject: Supplies order

```text
Good morning,

Our PO: MPO/3293.

We would like to place the following order:

- 250 small carton
- 30 carton Nitrile Gloves Large Box of 100 (same spec as our last order)
- 40 piece wodoen pallet
- half a dozen Edge Protectors 50x50x1200mm Bundle of 50 (same spec as our last order)

Delivery in 10 days would suit us.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/3293",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "small carton",
      "quantity": 250,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": "same spec as our last order",
      "product_text": "Nitrile Gloves Large Box of 100",
      "quantity": 30,
      "unit_price_text": null,
      "unit_text": "carton"
    },
    {
      "item_notes": null,
      "product_text": "wodoen pallet",
      "quantity": 40,
      "unit_price_text": null,
      "unit_text": "piece"
    },
    {
      "item_notes": "same spec as our last order",
      "product_text": "Edge Protectors 50x50x1200mm Bundle of 50",
      "quantity": 6,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "in 10 days"
}
```

oracle: route=exception  asks=[]  violations=['unresolvable_product']
focus: flag:mention_typo, route:exception, layout:dash_list, po_placement:body_only, quirk_a:canonical_unit, quirk_b:item_note

### 043 · TST-SCN-000428 · new_order

From: priya@swiftship.au    Sent: 2026-06-30T11:47:00+10:00
Subject: Order request – SwiftShip eCommerce

```text
Morning,

Hoping to get another order in:

- bubble wrap – 8 roll
- a4 box – 5025 each

Delivery ASAP would suit us.
Delivery address: Alexandria fulfilment centre.

Cheers,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": null,
  "delivery_address_text": "Alexandria fulfilment centre",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "bubble wrap",
      "quantity": 8,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "a4 box",
      "quantity": 5025,
      "unit_price_text": null,
      "unit_text": "each"
    }
  ],
  "notes": null,
  "requested_date_text": "ASAP"
}
```

oracle: route=exception  asks=[]  violations=['above_max']
focus: flag:qty_above_max, flag:unsigned, route:exception, layout:reverse_list, quirk_a:canonical_unit, quirk_c:unsigned_personal

### 044 · TST-SCN-000431 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-05-04T16:43:00+10:00
Subject: Restock for Redgum Furniture Co

```text
Order as follows:

- 1 padded envelopes
- 1 strapping buckles

We would need these 15 May.
Deliver to Dandenong plant.
Just a heads up: site induction required for drivers.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": null,
  "delivery_address_text": "Dandenong plant",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "padded envelopes",
      "quantity": 1,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "strapping buckles",
      "quantity": 1,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": "site induction required for drivers",
  "requested_date_text": "15 May"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:missing_po, route:touchless, layout:dash_list

### 045 · TST-SCN-000442 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-05-31T15:59:00+10:00
Subject: New order – Cairnwell Pharma Distribution

```text
Good morning,

We would like to place the following order:

- 1000 buckles strap clips
- 50 packs Address Labels 99x38mm Sheet Pack of 100 @ $14.50
- 4 edge protectors @ $68.00

We would need these in a fortnight.
Delivery address: Eagle Farm store.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": null,
  "delivery_address_text": "Eagle Farm store",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "strap clips",
      "quantity": 1000,
      "unit_price_text": null,
      "unit_text": "buckles"
    },
    {
      "item_notes": null,
      "product_text": "Address Labels 99x38mm Sheet Pack of 100",
      "quantity": 50,
      "unit_price_text": "$14.50",
      "unit_text": "packs"
    },
    {
      "item_notes": null,
      "product_text": "edge protectors",
      "quantity": 4,
      "unit_price_text": "$68.00",
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "in a fortnight"
}
```

oracle: route=exception  asks=[]  violations=['unresolvable_unit']
focus: flag:missing_po, flag:pack_size_trap, flag:prices_stated, route:exception, layout:dash_list

### 046 · TST-SCN-000456 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-02-24T13:06:00+11:00
Subject: Redgum Furniture Co – PO 4593912633

```text
Please supply:

- 12 rl steel strapping
- 72 roll TPE-CLR-201

Timing: 7 March.
Delivery address: Dandenong plant.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4593912633",
  "delivery_address_text": "Dandenong plant",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "steel strapping",
      "quantity": 12,
      "unit_price_text": null,
      "unit_text": "rl"
    },
    {
      "item_notes": null,
      "product_text": "TPE-CLR-201",
      "quantity": 72,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": "7 March"
}
```

oracle: route=exception  asks=[]  violations=['discontinued']
focus: flag:discontinued_item, route:exception, layout:dash_list, po_placement:subject_only, quirk_a:canonical_unit

### 047 · TST-SCN-000458 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-06-24T09:32:00+10:00
Subject: Cairnwell Pharma Distribution – PO MPO/7275

```text
Good morning,

Please book this against MPO/7275.

We would like to place the following order:

- 4x6 lbaels – 1 roll @ $18.50

Deliver to Unit 2, 41 Navigator Place, Eagle Farm QLD 4009.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/7275",
  "delivery_address_text": "Unit 2, 41 Navigator Place, Eagle Farm QLD 4009",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "4x6 lbaels",
      "quantity": 1,
      "unit_price_text": "$18.50",
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=exception  asks=[]  violations=['unresolvable_product']
focus: flag:qty_below_moq, flag:mention_typo, flag:prices_stated, route:exception, layout:reverse_list, po_placement:both, quirk_a:canonical_unit

### 048 · TST-SCN-000463 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-02-23T08:38:00+11:00
Subject: Order request – Redgum Furniture Co

```text
Please supply:

1 bag corner protectors (same spec as our last order)

Timing: 7 March.
Delivery address: Dandenong plant.
Please book this against 4513991432.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4513991432",
  "delivery_address_text": "Dandenong plant",
  "line_items": [
    {
      "item_notes": "same spec as our last order",
      "product_text": "corner protectors",
      "quantity": 1,
      "unit_price_text": null,
      "unit_text": "bag"
    }
  ],
  "notes": null,
  "requested_date_text": "7 March"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:x_list, po_placement:body_only, quirk_b:item_note

### 049 · TST-SCN-000468 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-03-26T16:21:00+11:00
Subject: Redgum Furniture Co – PO 4568110693

```text
Please send 360 rl of Brown Packing Tape 48mm x 75m and 8 roll of Machine Stretch Film 500mm x 1500m.

Deliver to Dandenong plant.
Please note: tailgate required.
Our PO: 4568110693.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4568110693",
  "delivery_address_text": "Dandenong plant",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Brown Packing Tape 48mm x 75m",
      "quantity": 360,
      "unit_price_text": null,
      "unit_text": "rl"
    },
    {
      "item_notes": null,
      "product_text": "Machine Stretch Film 500mm x 1500m",
      "quantity": 8,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": "tailgate required",
  "requested_date_text": null
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:prose, po_placement:both, quirk_a:canonical_unit

### 050 · TST-SCN-000479 · new_order

From: purchasing@orbitcomponents.com.au    Sent: 2026-05-28T10:14:00+10:00
Subject: New order – Orbit Components

```text
PO for this order: OC-3157-3.

Please supply:

30 ctns nitrile gloves
2 x strapping buckles
PAL-EUR-602 (usual ea, qty to follow)

Timing: in 5 days.
Deliver to Prestons overflow.

Regards,
Alan
```

gold_extraction:
```json
{
  "buyer_name_text": "Alan",
  "customer_po_text": "OC-3157-3",
  "delivery_address_text": "Prestons overflow",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "nitrile gloves",
      "quantity": 30,
      "unit_price_text": null,
      "unit_text": "ctns"
    },
    {
      "item_notes": null,
      "product_text": "strapping buckles",
      "quantity": 2,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "PAL-EUR-602",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": "ea"
    }
  ],
  "notes": null,
  "requested_date_text": "in 5 days"
}
```

oracle: route=clarification  asks=['quantity']  violations=[]
focus: flag:missing_quantity, route:clarification, layout:x_list, po_placement:body_only

### 051 · TST-SCN-000482 · new_order

From: josh@fernvalenurseries.com.au    Sent: 2026-03-06T10:45:00+11:00
Subject: Restock for Fernvale Nurseries

```text
Hi,

Can we get the following sorted please:

- 216 roll Brown Packing Tape 48mm x 75m at $2.40
- 8 steel strapping at $115.00
- 2 VFL-PPR-801 at $52.00

We would need these as soon as you can.

Cheers,
Josh
```

gold_extraction:
```json
{
  "buyer_name_text": "Josh",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Brown Packing Tape 48mm x 75m",
      "quantity": 216,
      "unit_price_text": "$2.40",
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "steel strapping",
      "quantity": 8,
      "unit_price_text": "$115.00",
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "VFL-PPR-801",
      "quantity": 2,
      "unit_price_text": "$52.00",
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "as soon as you can"
}
```

oracle: route=exception  asks=[]  violations=['discontinued']
focus: flag:discontinued_item, flag:prices_stated, route:exception, layout:dash_list, quirk_a:canonical_unit

### 052 · TST-SCN-000483 · new_order

From: dana.whitfield@harbourline.com.au    Sent: 2026-02-06T11:02:00+11:00
Subject: PO PO-52006 – Harbourline Logistics Pty Ltd

```text
Good morning,

We would like to order 25 pcs of big box at $2.10 and 288 Clear Packing Tape 48mm x 75m at $2.40.

Timing: in a fortnight.
Just a heads up: call before delivery.
PO for this order: PO-52006.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": "PO-52006",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "big box",
      "quantity": 25,
      "unit_price_text": "$2.10",
      "unit_text": "pcs"
    },
    {
      "item_notes": null,
      "product_text": "Clear Packing Tape 48mm x 75m",
      "quantity": 288,
      "unit_price_text": "$2.40",
      "unit_text": null
    }
  ],
  "notes": "call before delivery",
  "requested_date_text": "in a fortnight"
}
```

oracle: route=clarification  asks=['delivery_site']  violations=[]
focus: flag:ambiguous_site, flag:prices_stated, route:clarification, layout:prose, po_placement:both

### 053 · TST-SCN-000501 · new_order

From: josh@fernvalenurseries.com.au    Sent: 2026-03-03T14:12:00+11:00
Subject: Supplies order

```text
Hi,

Can you send over 60 roll of Hand Stretch Film 500mm x 400m Clear at $7.80 (no substitutions please) and 12 roll of Bubble Wrap Roll 500mm x 100m 10mm Bubble @ $42.00 (must be the heavy duty ones)?

Delivery address: Fernvale site.

Cheers,
Josh
```

gold_extraction:
```json
{
  "buyer_name_text": "Josh",
  "customer_po_text": null,
  "delivery_address_text": "Fernvale site",
  "line_items": [
    {
      "item_notes": "no substitutions please",
      "product_text": "Hand Stretch Film 500mm x 400m Clear",
      "quantity": 60,
      "unit_price_text": "$7.80",
      "unit_text": "roll"
    },
    {
      "item_notes": "must be the heavy duty ones",
      "product_text": "Bubble Wrap Roll 500mm x 100m 10mm Bubble",
      "quantity": 12,
      "unit_price_text": "$42.00",
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:prices_stated, route:touchless, layout:prose, quirk_a:canonical_unit, quirk_b:item_note

### 054 · TST-SCN-000535 · new_order

From: sam.oneill@metroprint.com.au    Sent: 2026-05-31T16:43:00+10:00
Subject: Restock for Metro Print Group

```text
Hello,

Could you please arrange the following for us:

- 4 roll plastic strapping
- Edge Protectors 50x50x1200mm Bundle of 50 (usual pack, qty to follow)
- 8 Padded Mailer 215x280mm Carton of 100
- 50 medium carton

Kind regards,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "plastic strapping",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "Edge Protectors 50x50x1200mm Bundle of 50",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": "pack"
    },
    {
      "item_notes": null,
      "product_text": "Padded Mailer 215x280mm Carton of 100",
      "quantity": 8,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "medium carton",
      "quantity": 50,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=clarification  asks=['quantity']  violations=[]
focus: flag:missing_po, flag:missing_quantity, flag:unsigned, route:clarification, layout:dash_list, quirk_a:canonical_unit, quirk_c:unsigned_personal

### 055 · TST-SCN-000544 · new_order

From: josh@fernvalenurseries.com.au    Sent: 2026-03-25T10:59:00+11:00
Subject: Order request – Fernvale Nurseries

```text
Hi,

Hoping to get another order in:

16 roll void fill

Delivery address: Fernvale site.
Please note: call before delivery.

Cheers,
Josh
```

gold_extraction:
```json
{
  "buyer_name_text": "Josh",
  "customer_po_text": null,
  "delivery_address_text": "Fernvale site",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "void fill",
      "quantity": 16,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": "call before delivery",
  "requested_date_text": null
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:x_list, quirk_a:canonical_unit

### 056 · TST-SCN-000548 · new_order

From: sofia@bightandbay.com.au    Sent: 2026-02-25T07:03:00+11:00
Subject: New order – Bight & Bay Seafoods

```text
Hi,

Order as follows:

10 each hardwood pallet

We would need these in 5 days.
Please note: deliver to rear dock.

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "hardwood pallet",
      "quantity": 10,
      "unit_price_text": null,
      "unit_text": "each"
    }
  ],
  "notes": "deliver to rear dock",
  "requested_date_text": "in 5 days"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:x_list, quirk_a:canonical_unit

### 057 · TST-SCN-000553 · new_order

From: alan.kwok@orbitcomponents.com.au    Sent: 2026-04-19T13:15:00+10:00
Subject: New order – Orbit Components

```text
Hi,

Order as follows:

288 x Clear Packing Tape 48mm x 75m
Medium Shipping Carton 400x300x250mm (qty to confirm)
144 roll TPE-FRG-203

Delivery in 10 days would suit us.
Delivery address: 14 Egerton Street, Silverwater NSW 2128.
Just a heads up: call before delivery.
Our PO: OC-0990-8.

Regards,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": "OC-0990-8",
  "delivery_address_text": "14 Egerton Street, Silverwater NSW 2128",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Clear Packing Tape 48mm x 75m",
      "quantity": 288,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Medium Shipping Carton 400x300x250mm",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "TPE-FRG-203",
      "quantity": 144,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": "call before delivery",
  "requested_date_text": "in 10 days"
}
```

oracle: route=clarification  asks=['quantity']  violations=[]
focus: flag:missing_quantity, flag:unsigned, route:clarification, layout:x_list, po_placement:body_only, quirk_a:canonical_unit, quirk_c:unsigned_personal

### 058 · TST-SCN-000578 · new_order

From: sofia@bightandbay.com.au    Sent: 2026-04-26T09:44:00+10:00
Subject: Restock for Bight & Bay Seafoods

```text
Order as follows:

- machine film – 4 roll
- Poly Mailer 310x405mm Carton of 500 – 6
- Void Fill Packing Paper 375mm x 450m – 104 roll
- padded bags – half a dozen carton

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "machine film",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "Poly Mailer 310x405mm Carton of 500",
      "quantity": 6,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Void Fill Packing Paper 375mm x 450m",
      "quantity": 104,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "padded bags",
      "quantity": 6,
      "unit_price_text": null,
      "unit_text": "carton"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=exception  asks=[]  violations=['above_max']
focus: flag:qty_above_max, route:exception, layout:reverse_list, quirk_a:canonical_unit

### 059 · TST-SCN-000585 · new_order

From: sofia@bightandbay.com.au    Sent: 2026-04-25T09:02:00+10:00
Subject: New order – Bight & Bay Seafoods

```text
Please send 416 roll of cuorier labels @ $18.50.

Just a heads up: tailgate required.

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "cuorier labels",
      "quantity": 416,
      "unit_price_text": "$18.50",
      "unit_text": "roll"
    }
  ],
  "notes": "tailgate required",
  "requested_date_text": null
}
```

oracle: route=exception  asks=[]  violations=['unresolvable_product']
focus: flag:qty_above_max, flag:mention_typo, flag:prices_stated, route:exception, layout:prose, quirk_a:canonical_unit

### 060 · TST-SCN-000596 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-04-15T10:57:00+10:00
Subject: Restock for Redgum Furniture Co

```text
Our PO: 4570222241.

Please supply:

- small box – 250
- Standard AU Pallet 1165x1165mm Hardwood – 10 pieces (same spec as our last order)
- gloves – 15
- packaging tape – 360 rl

Timing: ASAP.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4570222241",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "small box",
      "quantity": 250,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": "same spec as our last order",
      "product_text": "Standard AU Pallet 1165x1165mm Hardwood",
      "quantity": 10,
      "unit_price_text": null,
      "unit_text": "pieces"
    },
    {
      "item_notes": null,
      "product_text": "gloves",
      "quantity": 15,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "packaging tape",
      "quantity": 360,
      "unit_price_text": null,
      "unit_text": "rl"
    }
  ],
  "notes": null,
  "requested_date_text": "ASAP"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:reverse_list, po_placement:body_only, quirk_b:item_note

### 061 · TST-SCN-000599 · new_order

From: sofia@bightandbay.com.au    Sent: 2026-04-08T14:43:00+10:00
Subject: Restock for Bight & Bay Seafoods

```text
Hi,

Please send 200 units of CTN-MD-002 @ $1.60.

Timing: in a week.

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "CTN-MD-002",
      "quantity": 200,
      "unit_price_text": "$1.60",
      "unit_text": "units"
    }
  ],
  "notes": null,
  "requested_date_text": "in a week"
}
```

oracle: route=exception  asks=[]  violations=['price_mismatch']
focus: flag:prices_stated, flag:price_mismatch, route:exception, layout:prose

### 062 · TST-SCN-000614 · new_order

From: sam.oneill@metroprint.com.au    Sent: 2026-03-10T07:37:00+11:00
Subject: Metro Print Group – PO MPG-158166

```text
Hello,

We would like to place the following order:

200 each small box
6 rolls large bubble wrap

Kind regards,
Sam
```

gold_extraction:
```json
{
  "buyer_name_text": "Sam",
  "customer_po_text": "MPG-158166",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "small box",
      "quantity": 200,
      "unit_price_text": null,
      "unit_text": "each"
    },
    {
      "item_notes": null,
      "product_text": "large bubble wrap",
      "quantity": 6,
      "unit_price_text": null,
      "unit_text": "rolls"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:x_list, po_placement:subject_only, quirk_a:canonical_unit

### 063 · TST-SCN-000615 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-06-08T10:21:00+10:00
Subject: Cairnwell Pharma Distribution – PO MPO/4854

```text
Good morning,

Could you please arrange the following for us:

- 60 each Standard AU Pallet 1165x1165mm Hardwood
- 4 rl Void Fill Packing Paper 375mm x 450m
- 10 pack laser labels
- 36 roll hand wrap
- buckles (usual bags, qty to follow)

Timing: 15 June.
Ship to: Unit 2, 41 Navigator Place, Eagle Farm QLD 4009.
Please book this against MPO/4854.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/4854",
  "delivery_address_text": "Unit 2, 41 Navigator Place, Eagle Farm QLD 4009",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Standard AU Pallet 1165x1165mm Hardwood",
      "quantity": 60,
      "unit_price_text": null,
      "unit_text": "each"
    },
    {
      "item_notes": null,
      "product_text": "Void Fill Packing Paper 375mm x 450m",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": "rl"
    },
    {
      "item_notes": null,
      "product_text": "laser labels",
      "quantity": 10,
      "unit_price_text": null,
      "unit_text": "pack"
    },
    {
      "item_notes": null,
      "product_text": "hand wrap",
      "quantity": 36,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "buckles",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": "bags"
    }
  ],
  "notes": null,
  "requested_date_text": "15 June"
}
```

oracle: route=clarification  asks=['quantity']  violations=[]
focus: flag:missing_quantity, route:clarification, layout:dash_list, po_placement:both, quirk_a:canonical_unit

### 064 · TST-SCN-000624 · new_order

From: tom.barker@swiftshipgroup.com    Sent: 2026-06-03T08:39:00+10:00
Subject: Order request – SwiftShip eCommerce

```text
Hey,

Hoping to get another order in:

288 roll kraft tape @ $2.04
250 pieces CTN-MD-002 at $1.45
50 each Large Shipping Carton 500x400x350mm at $2.10

Delivery 15 June would suit us.

Cheers,
Tom
```

gold_extraction:
```json
{
  "buyer_name_text": "Tom",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "kraft tape",
      "quantity": 288,
      "unit_price_text": "$2.04",
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "CTN-MD-002",
      "quantity": 250,
      "unit_price_text": "$1.45",
      "unit_text": "pieces"
    },
    {
      "item_notes": null,
      "product_text": "Large Shipping Carton 500x400x350mm",
      "quantity": 50,
      "unit_price_text": "$2.10",
      "unit_text": "each"
    }
  ],
  "notes": null,
  "requested_date_text": "15 June"
}
```

oracle: route=exception  asks=[]  violations=['price_mismatch']
focus: flag:prices_stated, flag:price_mismatch, route:exception, layout:x_list, quirk_a:canonical_unit

### 065 · TST-SCN-000657 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-06-24T13:37:00+10:00
Subject: Order request – Cairnwell Pharma Distribution

```text
Good morning,

We would like to place the following order:

- Address Labels 99x38mm Sheet Pack of 100 (qty to confirm)
- 2 roll steel strapping
- 216 Fragile Printed Tape 48mm x 66m
- 202 carton bubble mailers
- 20 au pallet

Timing: 7 July.
Please book this against MPO/4566.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/4566",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Address Labels 99x38mm Sheet Pack of 100",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "steel strapping",
      "quantity": 2,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "Fragile Printed Tape 48mm x 66m",
      "quantity": 216,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "bubble mailers",
      "quantity": 202,
      "unit_price_text": null,
      "unit_text": "carton"
    },
    {
      "item_notes": null,
      "product_text": "au pallet",
      "quantity": 20,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": "7 July"
}
```

oracle: route=exception  asks=['quantity']  violations=['discontinued', 'above_max']
focus: flag:missing_quantity, flag:discontinued_item, flag:qty_above_max, route:exception, layout:dash_list, po_placement:body_only, quirk_a:canonical_unit

### 066 · TST-SCN-000662 · new_order

From: sam.oneill@metroprint.com.au    Sent: 2026-05-15T07:58:00+10:00
Subject: Restock for Metro Print Group

```text
Hello,

We would like to place the following order:

10 boxes plastic maliers at $55.00
1 rls Void Fill Packing Paper 375mm x 450m at $57.20

Delivery in 3 days would suit us.

Kind regards,
Sam
```

gold_extraction:
```json
{
  "buyer_name_text": "Sam",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "plastic maliers",
      "quantity": 10,
      "unit_price_text": "$55.00",
      "unit_text": "boxes"
    },
    {
      "item_notes": null,
      "product_text": "Void Fill Packing Paper 375mm x 450m",
      "quantity": 1,
      "unit_price_text": "$57.20",
      "unit_text": "rls"
    }
  ],
  "notes": null,
  "requested_date_text": "in 3 days"
}
```

oracle: route=exception  asks=[]  violations=['unresolvable_product', 'below_moq', 'price_mismatch']
focus: flag:missing_po, flag:qty_below_moq, flag:mention_typo, flag:prices_stated, flag:price_mismatch, route:exception, layout:x_list

### 067 · TST-SCN-000665 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-06-02T15:46:00+10:00
Subject: Redgum Furniture Co – PO 4561737163

```text
Hi,

Order as follows:

- strapping – 4
- Address Labels 99x38mm Sheet Pack of 100 – 50
- PAL-EUR-602 – 30 ea (no substitutions please)
- Steel Strapping 19mm x 300m – 12 roll
- heavy duty carton – 80 pcs

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4561737163",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "strapping",
      "quantity": 4,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Address Labels 99x38mm Sheet Pack of 100",
      "quantity": 50,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": "no substitutions please",
      "product_text": "PAL-EUR-602",
      "quantity": 30,
      "unit_price_text": null,
      "unit_text": "ea"
    },
    {
      "item_notes": null,
      "product_text": "Steel Strapping 19mm x 300m",
      "quantity": 12,
      "unit_price_text": null,
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "heavy duty carton",
      "quantity": 80,
      "unit_price_text": null,
      "unit_text": "pcs"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=exception  asks=[]  violations=['discontinued']
focus: flag:discontinued_item, route:exception, layout:reverse_list, po_placement:subject_only, quirk_a:canonical_unit, quirk_b:item_note

### 068 · TST-SCN-000673 · new_order

From: josh@fernvalenurseries.com.au    Sent: 2026-05-15T08:51:00+10:00
Subject: Supplies order

```text
Hey,

Hoping to get another order in:

- 12 roll machine wrap (no substitutions please)

Delivery in 10 days would suit us.
Deliver to 210 Banks Creek Road, Fernvale QLD 4306.

Cheers,
Josh
```

gold_extraction:
```json
{
  "buyer_name_text": "Josh",
  "customer_po_text": null,
  "delivery_address_text": "210 Banks Creek Road, Fernvale QLD 4306",
  "line_items": [
    {
      "item_notes": "no substitutions please",
      "product_text": "machine wrap",
      "quantity": 12,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": "in 10 days"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: route:touchless, layout:dash_list, quirk_a:canonical_unit, quirk_b:item_note

### 069 · TST-SCN-000675 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-04-03T13:59:00+11:00
Subject: Redgum Furniture Co – PO 4532359409

```text
Hi,

Please supply:

- Bubble Wrap Roll 500mm x 100m 10mm Bubble – 12 roll at $42.00
- Poly Strapping 12mm x 1000m – 4 @ $49.00
- Machine Stretch Film 500mm x 1500m – 32 rolls @ $64.00

Timing: in a week.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4532359409",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Bubble Wrap Roll 500mm x 100m 10mm Bubble",
      "quantity": 12,
      "unit_price_text": "$42.00",
      "unit_text": "roll"
    },
    {
      "item_notes": null,
      "product_text": "Poly Strapping 12mm x 1000m",
      "quantity": 4,
      "unit_price_text": "$49.00",
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "Machine Stretch Film 500mm x 1500m",
      "quantity": 32,
      "unit_price_text": "$64.00",
      "unit_text": "rolls"
    }
  ],
  "notes": null,
  "requested_date_text": "in a week"
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:prices_stated, route:touchless, layout:reverse_list, po_placement:subject_only, quirk_a:canonical_unit

### 070 · TST-SCN-000685 · new_order

From: helen.diaz@metroprint.com.au    Sent: 2026-03-02T15:57:00+11:00
Subject: New order – Metro Print Group

```text
Good morning,

Could you please arrange the following for us:

- shipping labels – 32 (must be the heavy duty ones)
- CTN-HD-004 – 40 each
- wide bubble wrap – 1 rl

Timing: in 5 days.

Kind regards,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": "must be the heavy duty ones",
      "product_text": "shipping labels",
      "quantity": 32,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": null,
      "product_text": "CTN-HD-004",
      "quantity": 40,
      "unit_price_text": null,
      "unit_text": "each"
    },
    {
      "item_notes": null,
      "product_text": "wide bubble wrap",
      "quantity": 1,
      "unit_price_text": null,
      "unit_text": "rl"
    }
  ],
  "notes": null,
  "requested_date_text": "in 5 days"
}
```

oracle: route=exception  asks=[]  violations=['below_moq']
focus: flag:missing_po, flag:qty_below_moq, flag:unsigned, route:exception, layout:reverse_list, quirk_a:canonical_unit, quirk_b:item_note, quirk_c:unsigned_personal

### 071 · TST-SCN-000689 · new_order

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-04-24T17:37:00+10:00
Subject: Redgum Furniture Co – PO 4510083362

```text
Hi,

Please send 8 edge protectors and 3 pack of LBL-ADR-302 (same spec as our last order).

We would need these in 5 days.
Ship to: Dandenong plant.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4510083362",
  "delivery_address_text": "Dandenong plant",
  "line_items": [
    {
      "item_notes": null,
      "product_text": "edge protectors",
      "quantity": 8,
      "unit_price_text": null,
      "unit_text": null
    },
    {
      "item_notes": "same spec as our last order",
      "product_text": "LBL-ADR-302",
      "quantity": 3,
      "unit_price_text": null,
      "unit_text": "pack"
    }
  ],
  "notes": null,
  "requested_date_text": "in 5 days"
}
```

oracle: route=exception  asks=[]  violations=['below_moq']
focus: flag:qty_below_moq, route:exception, layout:prose, po_placement:subject_only, quirk_a:canonical_unit, quirk_b:item_note

### 072 · TST-SCN-000693 · new_order

From: elaine.fox@cairnwellpharma.com    Sent: 2026-05-13T17:16:00+10:00
Subject: Cairnwell Pharma Distribution – PO MPO/8188

```text
Hello,

We would like to place the following order:

100 each medium carton

Kind regards,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": "MPO/8188",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "medium carton",
      "quantity": 100,
      "unit_price_text": null,
      "unit_text": "each"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```

oracle: route=touchless  asks=[]  violations=[]
focus: flag:unsigned, route:touchless, layout:x_list, po_placement:subject_only, quirk_a:canonical_unit, quirk_c:unsigned_personal

### 073 · TST-AMD-000001 · amendment / date_change

From: orders@harbourline.com.au    Sent: 2026-01-31T14:00:00+11:00
Subject: Change to our order

```text
Good morning,

Regarding PO PO-45390 – delivery in a fortnight would suit us better.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": "PO-45390",
  "delivery_address_text": null,
  "line_items": [],
  "notes": null,
  "requested_date_text": "in a fortnight"
}
```


### 074 · TST-AMD-000004 · amendment / add_item

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-04-06T14:37:00+10:00
Subject: Order amendment – Redgum Furniture Co

```text
Hi,

Re our PO 4599928960: please add 2 roll of Bubble Wrap Roll 500mm x 100m 10mm Bubble as well.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4599928960",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Bubble Wrap Roll 500mm x 100m 10mm Bubble",
      "quantity": 2,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 075 · TST-AMD-000005 · amendment / remove_item

From: sofia@bightandbay.com.au    Sent: 2026-02-19T16:43:00+11:00
Subject: Change to our order

```text
Hi,

Quick change to the order we placed this morning: please drop the courier satchels from it.

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "courier satchels",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 076 · TST-AMD-000009 · amendment / qty_change

From: alan.kwok@orbitcomponents.com.au    Sent: 2026-03-20T14:43:00+11:00
Subject: Change to our order

```text
Regarding PO OC-5422-9 – could we make the Thermal Shipping Labels 100x150mm Roll of 500 16 rls instead?

Regards,
Alan
```

gold_extraction:
```json
{
  "buyer_name_text": "Alan",
  "customer_po_text": "OC-5422-9",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Thermal Shipping Labels 100x150mm Roll of 500",
      "quantity": 16,
      "unit_price_text": null,
      "unit_text": "rls"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 077 · TST-AMD-000016 · amendment / add_item

From: sofia@bightandbay.com.au    Sent: 2026-06-30T13:36:00+10:00
Subject: Amendment to recent order

```text
Hi,

Regarding the order we placed this morning – could you also add 72 roll of packing tape to it?

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "packing tape",
      "quantity": 72,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 078 · TST-AMD-000018 · amendment / remove_item

From: sofia@bightandbay.com.au    Sent: 2026-04-06T14:33:00+10:00
Subject: Change to our order

```text
Regarding the order we placed this morning – please drop the gloves from it.

Thanks,
Sofia
```

gold_extraction:
```json
{
  "buyer_name_text": "Sofia",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "gloves",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 079 · TST-AMD-000023 · amendment / remove_item

From: tom.barker@swiftshipgroup.com    Sent: 2026-02-22T14:12:00+11:00
Subject: Order amendment – SwiftShip eCommerce

```text
Hey,

Quick change to yesterday's order: we no longer need the VFL-PPR-801 – please take it off.

Cheers,
Tom
```

gold_extraction:
```json
{
  "buyer_name_text": "Tom",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "VFL-PPR-801",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 080 · TST-AMD-000029 · amendment / add_item

From: tom.barker@swiftshipgroup.com    Sent: 2026-02-05T12:30:00+11:00
Subject: Change to our order

```text
Hi,

Regarding our order from Monday – could you also add 3 pks of Strapping Buckles 12mm Bag of 1000 to it?

Cheers,
Tom
```

gold_extraction:
```json
{
  "buyer_name_text": "Tom",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Strapping Buckles 12mm Bag of 1000",
      "quantity": 3,
      "unit_price_text": null,
      "unit_text": "pks"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 081 · TST-AMD-000036 · amendment / date_change

From: priya@swiftship.au    Sent: 2026-02-13T09:22:00+11:00
Subject: Change to our order

```text
Hey,

Regarding our order from Monday – sorry for the change – delivery in a fortnight works better for us.

Cheers,
Priya
```

gold_extraction:
```json
{
  "buyer_name_text": "Priya",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [],
  "notes": null,
  "requested_date_text": "in a fortnight"
}
```


### 082 · TST-AMD-000043 · amendment / remove_item

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-03-29T14:55:00+11:00
Subject: Change to our order

```text
Hi,

Re our PO 4545775383: please drop the Void Fill Packing Paper 375mm x 450m from it.

Regards,
Marcus
```

gold_extraction:
```json
{
  "buyer_name_text": "Marcus",
  "customer_po_text": "4545775383",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Void Fill Packing Paper 375mm x 450m",
      "quantity": null,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 083 · TST-AMD-000047 · amendment / add_item

From: priya@swiftship.au    Sent: 2026-04-04T11:25:00+11:00
Subject: Change to our order

```text
Hey,

Quick change to our order from Monday: could you also add 16 Poly Strapping 12mm x 1000m to it?

Cheers,
Priya
```

gold_extraction:
```json
{
  "buyer_name_text": "Priya",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Poly Strapping 12mm x 1000m",
      "quantity": 16,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 084 · TST-AMD-000054 · amendment / date_change

From: sam.oneill@metroprint.com.au    Sent: 2026-06-10T11:54:00+10:00
Subject: Change to our order

```text
Good morning,

Regarding PO MPG-745337 – delivery in a fortnight would suit us better.

Kind regards,
Sam
```

gold_extraction:
```json
{
  "buyer_name_text": "Sam",
  "customer_po_text": "MPG-745337",
  "delivery_address_text": null,
  "line_items": [],
  "notes": null,
  "requested_date_text": "in a fortnight"
}
```


### 085 · TST-AMD-000063 · amendment / add_item

From: tom.barker@swiftshipgroup.com    Sent: 2026-05-12T08:58:00+10:00
Subject: Amendment to recent order

```text
Morning,

Quick change to the order we placed this morning: please add 216 rls of Clear Packing Tape 48mm x 75m as well.

Cheers,
Tom
```

gold_extraction:
```json
{
  "buyer_name_text": "Tom",
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "Clear Packing Tape 48mm x 75m",
      "quantity": 216,
      "unit_price_text": null,
      "unit_text": "rls"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 086 · TST-AMD-000065 · amendment / qty_change

From: dana.whitfield@harbourline.com.au    Sent: 2026-03-26T11:41:00+11:00
Subject: Change to our order

```text
Good morning,

Re our PO PO-40534: please bump the bubble mailers to 1.

Kind regards,
Dana
```

gold_extraction:
```json
{
  "buyer_name_text": "Dana",
  "customer_po_text": "PO-40534",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "bubble mailers",
      "quantity": 1,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 087 · TST-AMD-000066 · amendment / date_change

From: tom.barker@swiftshipgroup.com    Sent: 2026-03-31T08:22:00+11:00
Subject: Change to our order

```text
Morning,

About the order we placed this morning: delivery in 5 days would suit us better.

Cheers,
```

gold_extraction:
```json
{
  "buyer_name_text": null,
  "customer_po_text": null,
  "delivery_address_text": null,
  "line_items": [],
  "notes": null,
  "requested_date_text": "in 5 days"
}
```


### 088 · TST-AMD-000079 · amendment / qty_change

From: elaine.fox@cairnwellpharma.com    Sent: 2026-01-28T12:36:00+11:00
Subject: Amendment to recent order

```text
Hello,

Quick change to PO MPO/7513: please bump the disposable gloves to 50.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/7513",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "disposable gloves",
      "quantity": 50,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 089 · TST-AMD-000086 · amendment / add_item

From: elaine.fox@cairnwellpharma.com    Sent: 2026-06-13T14:51:00+10:00
Subject: Amendment to recent order

```text
Hello,

Quick change to PO MPO/1667: could you also add 20 roll of big bubble to it?

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/1667",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "big bubble",
      "quantity": 20,
      "unit_price_text": null,
      "unit_text": "roll"
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 090 · TST-AMD-000094 · amendment / qty_change

From: elaine.fox@cairnwellpharma.com    Sent: 2026-04-29T17:24:00+10:00
Subject: Amendment to recent order

```text
Hello,

Re our PO MPO/2373: please bump the bubble mailers to 2.

Kind regards,
Elaine
```

gold_extraction:
```json
{
  "buyer_name_text": "Elaine",
  "customer_po_text": "MPO/2373",
  "delivery_address_text": null,
  "line_items": [
    {
      "item_notes": null,
      "product_text": "bubble mailers",
      "quantity": 2,
      "unit_price_text": null,
      "unit_text": null
    }
  ],
  "notes": null,
  "requested_date_text": null
}
```


### 091 · TST-CXL-000003 · cancellation

From: elaine.fox@cairnwellpharma.com    Sent: 2026-07-01T13:05:00+10:00
Subject: Order cancellation

```text
Hello,

Could you cancel our order from Monday for us?

Kind regards,
Elaine
```


### 092 · TST-CXL-000014 · cancellation

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-01-29T16:33:00+11:00
Subject: Please cancel our order

```text
Hi,

Please cancel PO 4571755444.

Regards,
Marcus
```


### 093 · TST-CXL-000019 · cancellation

From: alan.kwok@orbitcomponents.com.au    Sent: 2026-05-10T13:41:00+10:00
Subject: Order cancellation

```text
Hi,

We need to cancel PO OC-4550-5.

Regards,
Alan
```


### 094 · TST-CXL-000022 · cancellation

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-04-14T15:21:00+10:00
Subject: Cancellation – Redgum Furniture Co

```text
Could you cancel our order from Monday for us? Apologies for the mess-around.

Regards,
Marcus
```


### 095 · TST-CXL-000023 · cancellation

From: elaine.fox@cairnwellpharma.com    Sent: 2026-06-05T11:07:00+10:00
Subject: Cancellation – Cairnwell Pharma Distribution

```text
Hello,

Could you cancel PO MPO/0429 for us? Apologies for the mess-around.

Kind regards,
Elaine
```


### 096 · TST-CXL-000024 · cancellation

From: josh@fernvalenurseries.com.au    Sent: 2026-02-20T15:04:00+11:00
Subject: Please cancel our order

```text
Hi,

Please cancel the order we placed this morning.

Cheers,
Josh
```


### 097 · TST-CXL-000025 · cancellation

From: josh@fernvalenurseries.com.au    Sent: 2026-01-26T12:58:00+11:00
Subject: Please cancel our order

```text
Hey,

Please cancel the order we placed this morning.

Cheers,
Josh
```


### 098 · TST-CXL-000033 · cancellation

From: tom.barker@swiftshipgroup.com    Sent: 2026-03-21T09:33:00+11:00
Subject: Cancellation – SwiftShip eCommerce

```text
Morning,

Could you cancel the order we placed this morning for us?

Cheers,
Tom
```


### 099 · TST-CXL-000044 · cancellation

From: sofia@bightandbay.com.au    Sent: 2026-02-24T08:15:00+11:00
Subject: Please cancel our order

```text
Hi,

Please cancel the order we placed this morning.

Thanks,
Sofia
```


### 100 · TST-CXL-000047 · cancellation

From: sam.oneill@metroprint.com.au    Sent: 2026-07-02T10:34:00+10:00
Subject: Please cancel our order

```text
Good morning,

We need to cancel PO MPG-881912.

Kind regards,
Sam
```


### 101 · TST-INQ-000007 · inquiry / general

From: sofia@bightandbay.com.au    Sent: 2026-01-20T11:56:00+11:00
Subject: Question about supply

```text
Hi,

Do you deliver to regional Queensland, and how does freight get charged?

Thanks,
Sofia
```


### 102 · TST-INQ-000012 · inquiry / stock_check

From: purchasing@orbitcomponents.com.au    Sent: 2026-03-03T09:39:00+11:00
Subject: Stock query

```text
Quick one – is small bubble wrap available right now, and how fast could you get it to us?

Regards,
Alan
```


### 103 · TST-INQ-000021 · inquiry / general

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-05-27T12:08:00+10:00
Subject: Quick question

```text
Hi,

Could you send through your latest product catalogue?

Regards,
Marcus
```


### 104 · TST-INQ-000024 · inquiry / quote_request

From: elaine.fox@cairnwellpharma.com    Sent: 2026-03-05T07:28:00+11:00
Subject: Pricing request

```text
Good morning,

Could you put together a quote for:

- 360 x warning tape
- 10 x wooden pallet
- 16 x plastic strapping

Any volume pricing would be good to know.

Kind regards,
Elaine
```


### 105 · TST-INQ-000060 · inquiry / quote_request

From: priya@swiftship.au    Sent: 2026-05-23T11:34:00+10:00
Subject: Quote request

```text
Hey,

Can we get pricing on the following:

- 360 x brown packaging tape
- 8 x angle boards

Keen to see where the numbers land.

Cheers,
Priya
```


### 106 · TST-INQ-000061 · inquiry / stock_check

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-02-05T14:54:00+11:00
Subject: Stock query

```text
Do you have double wall box in stock at the moment? What sort of lead time are we looking at?

Regards,
Marcus
```


### 107 · TST-INQ-000074 · inquiry / general

From: elaine.fox@cairnwellpharma.com    Sent: 2026-04-06T08:31:00+10:00
Subject: Question about supply

```text
Good morning,

What is your cutoff for same day dispatch?

Kind regards,
Elaine
```


### 108 · TST-INQ-000076 · inquiry / quote_request

From: elaine.fox@cairnwellpharma.com    Sent: 2026-04-09T13:57:00+10:00
Subject: Quote request

```text
Hello,

Could you put together a quote for:

- 200 x small shipping box
- 360 x brown packaging tape
- 200 x medium box

Any volume pricing would be good to know.

Kind regards,
```


### 109 · TST-INQ-000078 · inquiry / general

From: priya@swiftship.au    Sent: 2026-04-03T09:29:00+11:00
Subject: Question about supply

```text
Hey,

Who is the best person to talk to about account pricing?

Cheers,
Priya
```


### 110 · TST-INQ-000089 · inquiry / quote_request

From: orders@harbourline.com.au    Sent: 2026-05-27T15:42:00+10:00
Subject: Quote request

```text
Hello,

Can we get pricing on the following:

- 108 x warning tape
- 80 x europallet
- 144 x kraft tape

Any volume pricing would be good to know.

Kind regards,
Dana
```


### 111 · TST-INQ-000091 · inquiry / stock_check

From: sofia@bightandbay.com.au    Sent: 2026-03-08T10:16:00+11:00
Subject: Stock query

```text
Hi,

Do you have packing tape in stock at the moment? What sort of lead time are we looking at?

Thanks,
Sofia
```


### 112 · TST-INQ-000094 · inquiry / stock_check

From: priya@swiftship.au    Sent: 2026-06-09T09:01:00+10:00
Subject: Stock query

```text
Hey,

Quick one – is fragile tape available right now, and how fast could you get it to us?

Cheers,
Priya
```


### 113 · TST-OTH-000000 · other / vendor_marketing

From: hello@apexgrowthpartners.com    Sent: 2026-07-02T12:43:00+10:00
Subject: A quick idea for your business

```text
Hi there,

We help suppliers like you win more repeat business online. Our team has run campaigns for over 300 Australian companies this year alone.

Would you be open to a free 15 minute chat this week?

Best,
Apex Growth Team
```


### 114 · TST-OTH-000015 · other / misdirected

From: marcus.yeo@redgumfurniture.com.au    Sent: 2026-06-28T14:03:00+10:00
Subject: Toolbox meeting

```text
Hi Sarah,

Just confirming Thursday's toolbox meeting has moved to the lunchroom. Can you let your crew know before knock-off?

Regards,
Marcus
```


### 115 · TST-OTH-000022 · other / courier_notice

From: noreply@fasttrackfreight.com.au    Sent: 2026-06-24T08:18:00+10:00
Subject: Delivery update – consignment CNS-987023

```text
Your consignment CNS-987023 is booked for delivery today between 9am and 1pm.
No signature is required for this delivery.

FastTrack Freight
```


### 116 · TST-OTH-000029 · other / courier_notice

From: noreply@fasttrackfreight.com.au    Sent: 2026-02-22T08:56:00+11:00
Subject: Delivery update – consignment CNS-961325

```text
Your consignment CNS-961325 is booked for delivery today between 9am and 1pm.
No signature is required for this delivery.

FastTrack Freight
```


### 117 · TST-OTH-000039 · other / vendor_marketing

From: talia@brightreach-media.com    Sent: 2026-06-01T15:58:00+10:00
Subject: A quick idea for your business

```text
Hi there,

We help suppliers like you win more repeat business online. Our team has run campaigns for over 300 Australian companies this year alone.

Would you be open to a free 15 minute chat this week?

Best,
Talia Reyes
```


### 118 · TST-OTH-000040 · other / vendor_marketing

From: talia@brightreach-media.com    Sent: 2026-04-27T14:46:00+10:00
Subject: Grow your wholesale pipeline

```text
Hi there,

We help suppliers like you win more repeat business online. Our team has run campaigns for over 300 Australian companies this year alone.

Would you be open to a free 15 minute chat this week?

Best,
Talia Reyes
```


### 119 · TST-OTH-000044 · other / misdirected

From: sam.oneill@metroprint.com.au    Sent: 2026-05-15T15:43:00+10:00
Subject: Toolbox meeting

```text
Hi Sarah,

Just confirming Thursday's toolbox meeting has moved to the lunchroom. Can you let your crew know before knock-off?

Kind regards,
Sam
```


### 120 · TST-OTH-000046 · other / courier_notice

From: noreply@fasttrackfreight.com.au    Sent: 2026-05-06T17:34:00+10:00
Subject: Delivery update – consignment CNS-944229

```text
Your consignment CNS-944229 is booked for delivery today between 9am and 1pm.
No signature is required for this delivery.

FastTrack Freight
```

