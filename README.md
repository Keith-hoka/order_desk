# order_desk

Logistics emails arrive as prose. ERPs need structured orders. This turns one
into the other, and puts a human in the loop where the model is unsure.

On this one narrow task, **3600 in-domain examples turn a 4B open model into
something that beats a prompted gpt-4o-mini by 12 F1 points on human-written
out-of-distribution emails**, and cuts its hallucination rate from 0.137 to
0.080 — at a fraction of the inference cost. The comparison is asymmetric on
purpose: one model is fine-tuned, the other is prompted. That asymmetry *is* the
case for fine-tuning a small model on a vertical task.

Around the model: a frozen eval harness, calibrated confidence, a human review
queue, a correction flywheel with two gates, a CI regression gate, and a
multi-tenant service shell.

## Results

Frozen evals, fixed by content hash: **synthetic** (n=1000, 800 with
extractions) and **human OOD** (n=65, 57 with extractions) — real emails written
by people, never used for training. Bootstrap 95% CIs in brackets.

The scorer itself is pinned by two known answers: feeding it the gold labels
scores 1.0, feeding it empty predictions scores 0.0. A metric you have not tried
to break is a metric you cannot trust.

| model | synthetic F1 | human OOD F1 | hallucination (OOD) | blended precision |
|---|---|---|---|---|
| qwen3-4b, prompted | 0.7168 | 0.7156 | — | — |
| qwen3-30b-a3b, prompted | 0.7708 | 0.8187 | — | — |
| gpt-4o-mini, prompted | 0.8485 | 0.8211 `[.767,.869]` | 0.137 | — |
| qwen3-4b + QLoRA (r=8) | 0.9978 | 0.9508 `[.927,.973]` | 0.090 | 0.50 |
| **qwen3-4b + flywheel** ← deployed | 0.9972 | 0.9418 `[.909,.967]` | 0.080 | **1.00** |

**The deployed model is not the one with the highest frozen-eval score.** It
gives up 0.009 F1 — well inside the bootstrap interval, i.e. indistinguishable
at n=65 — to eliminate an entire failure mode. On emails that blend an order
with an unrelated enquiry, the higher-scoring checkpoint extracts the enquiry as
a line item; precision on those goes **0.50 → 1.00**, while recall on
question-phrased genuine orders holds at 1.00 (no over-suppression). A frozen
eval cannot see that. A targeted gate can. → [Phase 9](docs/phase9_milestone.md)

Two more findings worth the space:

- **Rank ablation contradicts the synthetic score.** r=32 scores *higher* on
  synthetic (0.9989 vs 0.9978) and *lower* on human OOD (0.9446 vs 0.9508). The
  extra capacity overfits the synthetic distribution. r=8 ships, because the
  column that matters is the out-of-distribution one.
  → [rank ablation](docs/baselines/phase3_r16_breakthrough.md)
- **Data past ~1000 examples buys almost nothing.** On synthetic, r=16:
  500 → 0.9918, 1000 → 0.9957, 2000 → 0.9974, 3600 → 0.9975. Measured on
  synthetic only — the honest caveat is that the curve was never run on human
  OOD. → [data curve](docs/baselines/phase3_curve.md)

## What it does

.eml  →  ingest        MIME parsing, HTML→text, pluggable EmailSource
→  route         LangGraph: order / amendment / enquiry
→  extract       fine-tuned 4B adapter, constrained decoding (xgrammar)
→  calibrate     isotonic; per-field confidence bands
→  review        flagged vs clean queue, human decides in a Next.js UI
→  resolve       product text → SKU (exact, then fuzzy ≥80)
→  fulfil        ERP sink + Slack notification

Reviewer edits feed the flywheel: corrections become training examples, the
model retrains, and **two gates** decide whether it ships — a targeted gate (did
the fix work?) and a no-regression gate (did anything else break?). A **CI job**
reads the committed eval reports and fails the build if the production adapter
regresses beyond tolerance. → [Phase 10](docs/phase10_milestone.md)

## Run the demo

No GPU needed. The review queue is a committed seed of 66 exceptions produced by
one GPU run; the API reads it offline.

```bash
uv sync
cp .env.example .env                       # set JWT_SECRET (openssl rand -base64 32)
echo "REVIEW_QUEUE_PATH=data/review_queue.json" >> .env
uv run python scripts/reset_review_queue.py

uv run uvicorn order_desk.api.app:create_app --factory --port 8000   # terminal 1
```

```bash
cd web && npm install
cp .env.local.example .env.local           # AUTH_SECRET + the same JWT_SECRET
npm run dev                                # terminal 2
```

Open `localhost:3000`. Sign in as `demo-admin@order-desk.test` / `demo1234`.
Registering instead founds a new org with an empty queue — the sample queue
belongs to the demo org. `reset_review_queue.py` restores it after a demo.

Live extraction additionally needs the adapter served on a GPU (Modal + vLLM);
`scripts/modal_vllm.py`.

## What is honest about this

Every one of these is stated in the milestone docs too, not just here.

- **The flywheel's corrections are synthetic.** The mechanism, the gates and the
  retraining are real and tested. The 150 corrections were generated, not
  collected from human reviewers. This proves the loop, not reviewer-driven
  improvement.
- **Human OOD is n=65.** The CIs are wide. Every claim above is stated with one.
- **The ERP is a mock.** Vendor-specific, needs credentials, not reproducible.
  Slack is real (an outbound webhook is). Stripe is real, in test mode.
- **The classifier misroutes** emails that blend an order with a question —
  a routing-layer limit the extraction adapter cannot fix. Documented, not hidden.
- **Tenant isolation is application-layer**, keyed on `org_id`, not database RLS.
  Cross-tenant ids return *not found* rather than *forbidden*, so id enumeration
  reveals nothing — but a production deployment would push this into the DB.
- **Billing is subscription-only, test mode.** No metered billing, webhooks or
  invoice reconciliation.
- **UI accounts live in their own store**, separate from the API's tenancy model.
  Sign-in is credentials-only; invites are simplified (an admin sets a password).
- **The adapter is served from one Modal endpoint.** Single point of failure.

## Layout

| | |
|---|---|
| `src/order_desk/` | eval harness, SFT data, pipeline, API, flywheel, fulfilment |
| `web/` | Next.js review UI (server components, Auth.js, no token in the browser) |
| `scripts/` | training, eval, smoke tests, queue reset |
| `docs/` | one milestone per phase |
| `data/`, `results/` | frozen fixtures, committed eval reports |

323 tests. One milestone per phase:
[corpus notes](docs/corpus_notes.md) and [audit](docs/audit_report.md) (1) ·
[baselines](docs/baselines/phase2_milestone.md) (2) ·
[fine-tune](docs/baselines/phase3_milestone.md) (3) ·
[service](docs/phase4_milestone.md) + [calibration](docs/phase4_calibration.md) (4) ·
[pipeline](docs/phase5_milestone.md) (5) · [ingest](docs/phase6_milestone.md) (6) ·
[review UI](docs/phase7_milestone.md) (7) · [fulfilment](docs/phase8_milestone.md) (8) ·
[flywheel](docs/phase9_milestone.md) (9) · [CI gate](docs/phase10_milestone.md) (10) ·
[multi-tenancy](docs/phase11_milestone.md) (11).
