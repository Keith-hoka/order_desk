# Phase 8 milestone — downstream fulfillment (v1)

The last leg of the workflow: an approved order is resolved to catalog SKUs,
built into an ERP order, submitted to the order system, and the right people
are notified -- or the order is held for manual mapping and that is flagged.
This closes the loop from "an email arrived" to "the order is in the ERP and
someone knows."

## Product resolution (SKU)

Extraction is deliberately mention-level (Phase 1): the model emits the product
as written, never a SKU it might hallucinate. Resolution is a downstream
deterministic step (`fulfillment/resolve.py`): a normalized exact match on the
catalog's aliases and names, then a rapidfuzz fuzzy fallback above a
conservative threshold. Below threshold, a product is left unresolved and
flagged -- not guessed. This is where Phase 1's mention-level decision pays off:
the risky mapping happens against a catalog, not inside the model.

## ERP order and the atomicity rule

`build_erp_order` maps a resolved order to an ERP-shaped structure with SKUs,
catalog unit prices, and quantities validated against each product's moq/max.
An order is atomic (decision B): any unresolved product or any quantity
violation blocks the *entire* order rather than submitting a partial or invalid
one. A held order surfaces as a manual-mapping notification, not a silent
partial fulfillment.

`OrderSink` abstracts the destination, mirroring EmailSource: `LocalOrderSink`
writes JSON and returns a receipt (the reproducible mock ERP); a real ERP
(SAP/NetSuite/Odoo) is an interface stub -- vendor-specific and credentialed,
not reproducible here.

## Notifications

`Notifier` mirrors the tracing layer (Noop vs Langfuse): `MockNotifier` for
offline tests, `SlackWebhookNotifier` for the real path -- an outbound POST to a
Slack incoming webhook read from the environment. Outbound and self-contained,
so it is fully reproducible: anyone points the webhook at their own workspace.
Two events: ORDER_SUBMITTED (with PO, order id, line count, total) and
NEEDS_MAPPING (with the unresolved products / quantity issues).

## Integration

Approving an exception triggers the fulfillment path
(resolve -> build -> submit-or-hold -> notify), guarded so it runs only when a
sink and notifier are configured and error-safe so a fulfillment failure never
fails the approval. The approve response carries the outcome (submitted with an
order id, or held with the unresolved list) for the UI to show.

## End-to-end (real Slack)

The smoke ran two orders through the real path: a clean order (cartons above
moq) was submitted to the ERP and posted ORDER_SUBMITTED to Slack
("PO-73218 accepted ... $167.50"); a held order (an unknown product) was blocked
and posted NEEDS_MAPPING ("held for manual mapping ... artisanal unobtainium
widget"). Both outcomes were delivered to the channel.

## v1

This completes the end-to-end vertical AI workflow: email in -> standardize ->
classify + route -> extract (fine-tuned adapter) -> human review -> resolve to
SKU -> submit to ERP (or hold) -> notify. Every stage is eval-covered,
reproducible, and honest about its boundaries. Tagged v1.0.

Remaining roadmap: Phase 9 (flywheel -- reviewer edits become retraining data),
Phase 10 (production + CI eval-regression gate), Phase 11 (SaaS).
