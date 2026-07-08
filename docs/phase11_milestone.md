# Phase 11 milestone — multi-tenant SaaS skeleton (v3)

The service becomes multi-tenant and billable: requests are scoped to an org,
usage is metered per org, plan quotas are enforced, and orgs subscribe to a plan
through Stripe. This is a deliberate *skeleton* -- it proves the SaaS shape
(tenancy, scopes, metering, quota, billing) with honest edges, without turning
the project into a billing product and diluting the ML core that is the
headline. Phase 4 anticipated this: its auth deferred scopes "to the
multi-tenant Phase 11, where they are actually needed." This phase delivers on
that.

## Org-scoped auth (fulfils Phase 4's deferred scopes)

`Principal` gains `org_id` and `scopes`; tokens carry them; `require_scope`
enforces a scope per endpoint (403 without it). An `Org` is a billing tenant, a
`User` belongs to an org, and role -> scope mapping (member vs admin) issues the
right scopes. The extension is backward-compatible: pre-tenancy tokens still
decode (org_id None, no scopes), and auth-disabled dev runs skip scope checks --
so nothing that worked before breaks.

## Per-org usage metering (SQLite, durable)

Usage is billing data, so it survives restarts: `SqliteMeteringStore` records
extraction count and input/output tokens per org and billing period (year-month)
via an atomic UPSERT, safe under concurrent requests. `/extract` records usage
after each successful extraction (guarded -- only for org-scoped requests). An
in-memory store backs tests and dev; the app uses SQLite when a db path is set.

## Plan quotas (enforced locally)

A `SqliteOrgStore` holds each org's plan durably (upsert = upgrade). Before an
extraction runs, `enforce_quota` compares the org's usage this period against its
plan quota (free 100, pro 10k, enterprise 1M) and rejects with 429 and an upgrade
hint when the org is at the cap. Quota lives locally -- Stripe owns the
subscription and the monthly price, the service owns usage limits. That split
keeps the hot path (quota check) free of a network call to Stripe.

## Stripe subscription billing (test mode, real)

`BillingClient` mirrors the Notifier pattern: `MockBillingClient` for tests and
CI, `StripeBillingClient` for the real path via Stripe's v1 namespace
(stripe 15.x). Product and per-plan prices are provisioned idempotently by
`lookup_key`, so the code is self-contained -- first run creates them, later runs
reuse them, no manual Dashboard setup. The smoke ran against Stripe test mode end
to end: provisioned the three prices, created a customer with a test card
(pm_card_visa), subscribed it to Pro, and read back an *active* subscription --
visible in the Stripe test Dashboard, no real charge. Like the Phase 8 Slack
path, this is a real integration, reproducible by pointing a test key at it.

Building it against the live API surfaced real behaviour a mock never would: a
subscription needs a default payment method, and attaching a shared test token
clones it to a customer-scoped id that must be used as the default. Those are
exactly the edges real billing integration has to handle.

## Honest scope

This is a subscription skeleton, and its edges are stated plainly:
- **Tenant isolation is at the application layer** (org_id keys), not database
  row-level security -- a production deployment would add RLS.
- **Billing is subscription-based, in test mode.** Usage-based (metered) billing,
  webhook handling (subscription lifecycle events), and invoice reconciliation
  are production extensions, not built here.
- **Quotas are enforced locally**, decoupled from Stripe; a production system
  might reconcile the two.

What is genuinely demonstrated: the multi-tenant shape end to end -- org-scoped
identity and permissions, durable per-org metering, plan-based quota
enforcement, and a real (test-mode) Stripe subscription flow.

## v3

Phase 11 wraps the self-improving ML system (v2) in a multi-tenant, billable
shell: orgs, scopes, metering, quotas, and Stripe subscriptions, with honest
boundaries throughout. Tagged v3.0.

This completes the planned build. The ML core remains the headline -- an
eval-driven vertical workflow with a fine-tuned adapter that beats a frontier
mini model, a review UI, downstream fulfilment, a correction flywheel, and a CI
regression gate -- now shown to be packageable as a multi-tenant product.
