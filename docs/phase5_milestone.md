# Phase 5 milestone — pipeline orchestration

The learned extraction node wrapped in a complete deterministic pipeline: a
LangGraph StateGraph that classifies each email, routes it declaratively, and
calls the fine-tuned adapter only for order-bearing mail. This turns "a strong
extraction model" into "a routed, observable, eval-covered vertical workflow."

## Architecture

START -> classify -> [conditional edge on route]
|- EXTRACT  -> extract -> finalize -> END
|- CANCEL   -> cancel  -> finalize -> END
|- INQUIRY  -> (mark)  -> finalize -> END
|- DISCARD  -> (mark)  -> finalize -> END

- **classify** (gpt-4o-mini, structured-outputs enum, the snapshot-pinned
  Phase 2 prompt) writes classification + route. Chosen over self-hosted Qwen
  for its far better human-OOD classification (0.846 vs 0.646) -- classify is
  the first gate.
- **route** is a declarative conditional edge reading state.route, not
  if-else in a function. Only the EXTRACT branch reaches the learned node, so
  inquiries and cancellations never spend an adapter call.
- **extract** (the fine-tuned adapter, Phase 4 client) runs only for orders;
  flags a blend ask when the body contains a product inquiry.
- **finalize** records policy violations (deterministic contract checks).

Routing is a pure function of class, so routing accuracy is measurable
against gold with no new annotation. State is a pydantic model (extra
forbidden); every node is a pure State -> dict update, fully offline-testable
with injected fakes.

## Routing evaluation (offline, reusing Phase 2 classification)

The classify node is the same prompt/model/enum as the Phase 2 baseline, so
those committed predictions are exactly what it produces -- routing is scored
offline at zero cost.

| set | routing accuracy | classification accuracy | route gap |
|---|---|---|---|
| synthetic (n=1000) | 1.0000 | 0.9980 | +0.0020 |
| human OOD (n=65) | 0.8923 | 0.8462 | +0.0462 |

The route gap is the insight: several classes map to one route (new_order and
amendment both -> EXTRACT), so a class error that preserves the route is not a
routing error. On synthetic the 0.2% classification error is entirely route-
harmless (routing 100%). On human, folding through the route map recovers 4.6
points -- the pipeline tolerates class confusion within a route equivalence
class.

## Failure mode: blended emails misclassified as inquiry

Human route confusion: **extract->inquiry: 6**. Six order emails whose
subjects carry a question signal ("packing peanuts?", "is email the right
channel?") are classified as inquiry and routed away from extraction -- real
routing errors where an order would be missed. This is the Phase 2 human-OOD
classification weakness surfacing at the routing layer.

## Over-extraction capture (strategy A) and its honest limit

The fine-tune over-extracts on blended order+question emails (a product
question's items get pulled into the order). Strategy A extracts normally but
flags a blend ask on a **product-inquiry heuristic** ("do you stock", "size
question") -- not a bare question mark, so polite questions ("could you
confirm?") do not trip it. On the live smoke this worked: the blended email
was extracted (bubble wrap included, the known over-extraction) **and** flagged
for review. Of 12 human order emails with a question mark in the body, the
heuristic flags only the 2 with genuine product questions.

**The honest limit:** the blend ask fires in the extract node, so it can only
catch blended emails that were classified as orders. The 6 emails above were
classified as inquiry and never reached extract, so the ask cannot flag them.
Strategy A covers "correctly-an-order but blended," not "blended but
misclassified as inquiry" -- the latter is a classification problem, for a
future flywheel signal, not the routing layer.

## What this buys

- Non-order mail costs no adapter call (declarative routing skips the learned
  node for inquiry/cancellation/other).
- Routing is robust to route-harmless misclassification (+4.6 pts on human).
- Over-extraction is captured and flagged where the model is asked to extract,
  turning a silent bug into a reviewable exception (the basis for Phase 7's
  exception queue).

## Exit

A LangGraph pipeline with declarative routing, a policy contract, and offline
route evaluation over both frozen sets. 207 tests. Remaining: Phase 6 (real
email ingest/threading), Phase 7 (exception-queue UI consuming per-field
confidence + blend asks), onward.
