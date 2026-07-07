# Phase 7 milestone — exception review UI

The human-in-the-loop layer: a Next.js review desk over a FastAPI backend that
turns every prior phase's exception signals -- per-field confidence (Phase 4),
blend and reply-history asks (Phase 5/6), policy violations -- into a queue a
reviewer can act on. This is where the pipeline's flags stop being internal
state and become work someone does.

## Priority: what most needs a human

The core is not the frontend but the triage logic (`review/priority.py`). It
integrates three signals into one priority, weighted so a policy violation
outranks an ask, which outranks a moderate-confidence field:

- **Band fields** -- raw confidence in [0.80, 0.95], the range Phase 4 found is
  only ~40% correct. Lower-confidence fields were all correct and higher ones
  are trustworthy, so band-membership, not lowest confidence, flags a field.
- **Asks** -- the model's own uncertainty flags (blend, reply-history).
- **Violations** -- policy contract breaches.

Calibrated confidence (Phase 4 isotonic) is carried for display but does not
drive ranking: it is in-sample and flat across the sparse band, so it informs
without deciding (decision B).

## Backend

The review API extends the Phase 4 service: `GET /exceptions` (priority-
sorted), `GET /exceptions/{id}`, `POST /exceptions/{id}/review`
(approve/edit/reject with structured edits). A ReviewStore abstracts the queue
source -- a pre-built JSON queue in production (built offline from the human
.eml corpus through the pipeline, so serving does not re-run OpenAI + Modal),
an in-memory store in tests. JWT-guarded, CORS-enabled for the Next.js origin.

## Frontend

A two-pane desk (queue + detail) in Next.js with a deliberate visual identity:
warm-paper background, IBM Plex Sans/Mono, restrained shipping-blue / brick /
amber signals -- not a templated SaaS look. Each exception surfaces *why* it
was flagged in plain language rather than a score; confidence badges appear
only on fields inside the actionable band, so a high-but-uniform confidence
(xgrammar inflation) shows nothing and the reviewer's attention goes to the
genuinely uncertain fields.

## What the real queue shows

Running the 66 packed human emails through the pipeline: 9 flagged, 57 clean.
Most extractions are good (Phase 3 human OOD headline 0.951), so the queue is
exactly the minority that needs review -- the point of an exception queue. The
top item is the constructed reply ("72 rolls please, same as last time.") whose
reply-history ask ranks it first: a reply whose order references conversation
history the model never saw, surfaced for the reviewer rather than silently
extracted from partial context. Below it sit the confidence-band items; the
clean majority sinks to priority 0.

## Exit

A working review desk: priority-sorted exceptions, why-flagged surfacing,
in-band confidence, and approve/edit/reject persisted through the API. The
triage logic is offline-tested; the UI runs against the live backend. Remaining
phases: 8 (mock ERP + Slack), 9 (flywheel -- reviewer edits become retraining
data), onward.
