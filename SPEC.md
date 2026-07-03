# order_desk — Specification (v1)

Email-to-order AI workflow for logistics. Inbound customer emails are
classified, structured into validated JSON orders by a fine-tuned model, and
routed to a touchless ERP path, a clarification loop, or a human exception
queue.

Positioning: a vertical AI workflow in which document extraction is one stage —
the only learned "deep" stage — surrounded by deliberately thin deterministic
stages. Not a horizontal extraction API.

## 1. Pipeline (v1)

ingest → classify → extract → validate → route

1. **Ingest** — inbound email webhook (Postmark/SendGrid Inbound Parse) →
   `POST /inbound`. MIME parse, HTML→text, signature strip, reply-chain strip.
   Attachments are stored from day one but not processed in v1; attachment-only
   emails route to the exception queue (reason `attachment_only`).
   Threading via reference ID in subject/body, `In-Reply-To` as fallback.
2. **Classify** — prompted enum via constrained decoding on the served model:
   `new_order | amendment | cancellation | inquiry | other`.
   Non-order routing: cancellation → lightweight match-and-flag path;
   inquiry/other → exception queue.
3. **Extract** — fine-tuned Qwen3-4B (QLoRA adapter) → schema-conditioned JSON
   with nested line items. xgrammar-constrained decoding; repair fallback.
4. **Validate** — deterministic, two layers: completeness (required fields
   present, non-null) and business rules (SKU in catalog, quantity ranges,
   date validity, address parseability, stated unit prices vs list price).
   List price is a v1 simplification -- real B2B price truth lives in quotes
   and contract pricing, which v1 does not model -- so price disputes route
   to the exception queue for a human, never to automated clarification.
5. **Route** —
   - sender domain resolves to no known customer → **exception queue**
     (reason `unknown_sender`)
   - missing required fields → **clarification email** (quotes original, lists
     exactly the missing fields; the reply re-enters ingest via thread ref)
   - critical field below confidence threshold, or rule violation →
     **exception queue** (HITL)
   - all checks pass → **touchless**: mock-ERP write, customer confirmation
     email (extracted summary + reference ID), internal Slack notification
6. **Flywheel (v2)** — human corrections, ERP rejections, and clarification
   replies become SFT pairs → retrain → eval gate → adapter registry → deploy.

## 2. Depth principle

Exactly one learned component (the extraction fine-tune) receives full ML
rigor: baselines, ablations, per-field error analysis, calibration. Every
other stage is prompted or deterministic and stays that way unless an eval
gate proves it insufficient (e.g., classification is promoted into the SFT
mix only if prompted accuracy misses target).

## 3. Target metrics

"Provisional" targets are locked or revised immediately after Phase 2
baselines; the binding requirement is always the documented comparison, not
the absolute number.

### Business (end-to-end, frozen-test replay)
| Metric | Target |
|---|---|
| STP (touchless) rate | ≥ 80% of corpus ceiling* (provisional) |
| Error escape rate — order reaches ERP untouched with ≥1 wrong field | ≤ 1% (hard) |
| Exception rate | measured; tuned against error escape via thresholds |
| Cycle time (excl. clarification wait) | measured |

*corpus ceiling = fraction of emails fully processable without human input,
by construction of the synthetic corpus.

### Stage-level
| Metric | Target |
|---|---|
| Classification accuracy / macro-F1 | ≥ 95% / ≥ 0.93 (provisional) |
| Order-missed rate (true order classified as non-order) | ≤ 1% |
| JSON schema validity | 100% under constrained decoding; repair-path rate measured |
| Extraction field-level micro-F1 (fine-tuned) | ≥ 0.92 (provisional) and ≥ gpt-4o-mini − 2 pts |
| Line-item alignment F1 | ≥ 0.90 (provisional) |
| Clarification decision | missed-field ≤ 2% at over-ask ≤ 15% (provisional) |
| Threading accuracy (reply → correct thread) | ≥ 99% |
| Confidence calibration (field-level ECE) | ≤ 0.08 (provisional) |

### Serving
| Metric | Target |
|---|---|
| p95 end-to-end per email, warm | ≤ 30 s |
| Cold start | measured & reported separately |
| Cost per 1k emails | measured; reported vs gpt-4o-mini pipeline with a volume curve |

No "always cheaper than gpt-4o-mini" claim at demo scale; the cost story is
the volume curve plus self-hosting/privacy/latency and robustness on noisy
input.

## 4. Non-goals (v1)
- Attachment *processing* is tiered and deferred: v1 stores attachments but
  processes email body text only. Tier 1 (born-digital PDF → text) lands in
  v1.5; Tier 2 (scanned PDF / image OCR) lands in v2 as the flywheel's
  distribution shift; Tier 3 (VLM direct image→JSON) is out of scope — the
  OCR+text-LLM architecture is retained deliberately. No EDI.
- Single vertical (logistics order desk). No second domain.
- Mock ERP only (own service with validation + rejection reasons). No real ERP.
- No IMAP / Gmail-OAuth ingestion; webhook inbound only.
- English-only corpus (multilingual is a v2+ stretch).
- No fraud / risk-scoring stages of any kind.
- Single-tenant operation — but tenant-aware schema from day one (§5).
- No real payment rails before Phase 11.

## 5. Data model — tenant-aware from day one

Every table carries `org_id` (FK → `orgs`). v1 runs with a single org row;
all queries are org-scoped from the first migration. Retrofitting later means
a full-table migration plus a query-by-query audit — refused.

Core tables (sketch; detailed DDL lands in the phase that owns each table):
`orgs`, `api_keys`, `threads`, `emails`, `attachments`, `classifications`, `extractions`,
`orders`, `corrections`, `jobs`, `adapters`, `usage_events`.
`extractions.source_type ∈ {email_body, pdf_text, ocr_text}` from the first
migration; `attachments` rows carry `(org_id, email_id, filename, mime, size,
sha256, storage_ref)`.

Inbound-address → org resolution is a lookup, not a constant.

## 6. usage_events ledger

Append-only from day one:
`(id, org_id, event_type, quantity, unit, ts, metadata jsonb)`.
Initial event types: `email_processed`, `classification_run`,
`extraction_run`, `tokens_in`, `tokens_out`, `clarification_sent`,
`confirmation_sent`, `erp_write`, `attachment_stored`
(reserved for later tiers: `pdf_parsed`, `ocr_run`).
This ledger is the billing source of truth for Phase 11. Langfuse is
observability, not billing.

## 7. Eval discipline
- The frozen evaluation set, locked in Phase 1, has three parts: (1) the full
  synthetic test split — 1,000 emails, machine contract-verified, generated
  from split-independent streams (train 4,500 / val 500 / test 1,000, so
  train can grow without touching the freeze), sha256-pinned in
  data/corpus/MANIFEST.json and gated in CI; (2) a human-certified subsample
  (~120 of those emails, audited in step 1.8); (3) a human-authored OOD slice
  (test_human.jsonl, ~40–60 emails written and gold-labelled by hand against
  the same fixtures). None of it is trained on; changing frozen bytes
  requires an explicit refreeze recorded in docs/frozen_test_fixlog.md.
- Baselines (Phase 2) precede any fine-tuning claim.
- Adapter deploys are eval-gated: a new adapter must be ≥ current on the
  frozen set overall, with no per-field regression beyond threshold.
- Simulated corrections in the flywheel are labeled as simulated in all
  reporting.

## 8. Releases
- **v1 (demo spine)** — Phases 0–8: ingest → … → mock ERP + Slack, exception UI.
- **v1.5 (attachments tier 1)** — Phase 8.5: born-digital PDF POs via
  layout-aware text/table extraction into the same pipeline; single order
  generator, dual renderers (email text / PDF) — interface fixed in Phase 1.
- **v2 (flywheel + production)** — Phases 9–10: OCR tier 2 as the
  motivating distribution shift, retrain loop, deploy, CI eval gate.
- **v3 (SaaS)** — Phase 11: org/user auth, Stripe (test mode), metering + quota.

## 9. Stack
Python 3.12 · uv · FastAPI · LangGraph · Postgres · Redis · Next.js ·
vLLM on Modal (serving, scale-to-zero) · TRL + PEFT + bitsandbytes on rented
GPU (training) · Langfuse · Postmark or SendGrid inbound · Resend or Postmark
outbound · GitHub Actions.

## 10. Risks
1. Fine-tuned 4B may not beat gpt-4o-mini on raw F1. Not a kill condition —
   the claim becomes the volume-cost curve, latency, self-hosting/privacy,
   and robustness on noisy email text. This framing is decided right after
   Phase 2, not retro-fitted.
2. Synthetic corpus realism. Mitigations: explicit noise taxonomy, style
   diversity, a human-verified frozen slice, and honest labeling of what is
   synthetic in all reporting.
3. Flywheel corrections are simulated absent real users — stated plainly.
4. Single developer; scope creep is the main schedule risk. §4 non-goals are
   the guardrail.
5. OCR quality is a confounding variable once tier 2 lands: the OCR engine
   gets its own mini-bake-off and stage metrics before any model claims are
   made on OCR'd slices.
