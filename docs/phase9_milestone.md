# Phase 9 milestone — the flywheel

Reviewer corrections become retraining signal, closing the loop from human
review back to a better model. This phase builds the mechanism end-to-end and
proves it on a controlled failure mode, with an eval gate that surfaces the
real tradeoff rather than hiding it -- and a base-size ablation that answers a
sharp question with a counter-intuitive result.

## Mechanism: corrections -> retraining

- **Correction extraction** (`flywheel/corrections.py`): an edited review item
  reconstructs the corrected extraction by applying its field-path edits to the
  original -- the new gold. Edited items are adapter re-extraction targets;
  rejected items are excluded, since a rejection is usually a classification
  signal ("not an order") rather than an adapter signal ("extract it
  differently"). Feeding rejections as extraction targets would be wrong signal.
- **Correction -> SFT** merges the corrected examples into the training pool,
  reusing the Phase 3 SFT format, and retrains with the existing Phase 3
  pipeline (upload + train, only the subset changes). The flywheel does not
  reinvent training; it feeds new data through the same path.

## Controlled failure mode: blended over-extraction

Blended over-extraction is a known adapter weakness (Phase 3): on an email that
orders X and merely asks about Y, the fine-tune pulls Y into the order. In real
mail this is rare (the human slice's question-mark orders are process questions
or polite ordering), so a controlled slice is constructed
(`flywheel/blended.py`): an order plus a genuine inquiry about a
different-category product, with gold containing only the ordered product.
About 22% are counter-examples -- question-phrased genuine orders whose product
*is* in the gold -- to teach the semantics (intent to order) rather than a
surface rule (a question mark means skip). It is labelled as a deliberately
synthetic, controlled failure mode.

## Gate 1 -- targeted improvement

On the held-out blended slice, line-item precision on non-counter cases (the
over-extraction metric: a pulled-in inquiry product is a false-positive line):

| | base full-r8 | flywheel-full-r8 |
|---|---|---|
| non-counter precision | 0.50 | 1.00 |
| counter recall | 1.00 | 1.00 |

The base over-extracts on every non-counter case (precision 0.50 -- it emits
the inquiry product too). The flywheel eliminates it (1.00) while holding
counter-example recall at 1.00 -- it did not learn "skip on a question mark,"
it learned the intent. The counter-examples worked. **Gate 1 PASS.**

## Gate 2 -- no regression (and the honest tradeoff)

On the frozen eval (Phase 1 synthetic n=1000 + human OOD n=65), micro-F1:

| | base full-r8 | flywheel-full-r8 | delta |
|---|---|---|---|
| synthetic | 0.9978 | 0.9972 | -0.0006 |
| human OOD | 0.9508 | 0.9418 | -0.0090 |

Synthetic is unchanged. Human OOD drops 0.009 -- within the 0.01 tolerance, but
real, and not hidden: it is mainly one parse failure (56/57 vs 57/57), not a
systemic extraction regression (hallucination actually fell, 0.0798 vs 0.0895).
The targeted gain carries a small OOD cost, and the gate's job is to surface
that tradeoff so the decision is informed. **Gate 2 PASS within tolerance.**

## Base-size ablation: does a smaller base help?

A sharp question: would a smaller base (500) -- Phase 3 showed 500 already
saturates synthetic -- give corrections more relative weight and a better
tradeoff? A flywheel-500-r8 was trained (500 base + the same 150 corrections)
and compared on every axis:

| | flywheel-full-r8 | flywheel-500-r8 |
|---|---|---|
| blended precision | 1.00 | 0.92 |
| human OOD F1 | 0.9418 | 0.9392 |
| synthetic F1 | 0.9972 | 0.9879 |
| human hallucination | 0.0798 | 0.1064 |

**Full base wins on every axis** -- and not only on general extraction: it
learns the *targeted fix better too* (blended 1.00 vs 0.92) and hallucinates
less. The finding: correction-integration quality depends on base quality. A
stronger base integrates targeted corrections more precisely; a weaker base
integrates them only partially (8% residual over-extraction). The intuition
that a smaller base gives corrections more weight and so learns them better is
refuted -- base quality is the precondition for correction effectiveness.

## Deployment decision

Both gates pass and the ablation confirms the base choice, so flywheel-full-r8
is promoted (`data/flywheel/adapter_registry.json`): the flywheel adapter
becomes the production adapter, with the gate evidence and the -0.009 OOD
tradeoff recorded.

## Honest scope

**The corrections are synthetic, not real human-in-the-loop edits.** Two things
must be kept separate:

- The *extraction mechanism* (`flywheel/corrections.py`) is real and tested: it
  turns an edited review item into corrected gold by applying the reviewer's
  field edits. If a reviewer edited exceptions in the Phase 7 UI, this is the
  code that would convert those edits into training signal.
- The *150 corrections actually fed into retraining* are **not** produced by
  anyone editing in the UI. They are programmatically generated
  (`flywheel/blended.py`) to model the scenario "a reviewer corrected a blended
  over-extraction." No order was hand-edited through the front end; the review
  store was not populated by real review sessions.

So this phase proves the **mechanism and the gate** on a controlled failure
mode with modelled corrections -- not a real reviewer-driven improvement, and
not a production-scale accumulation. A real flywheel needs enough genuine
corrections from production review sessions; a handful of real edits would not
move the model measurably, which is why a controlled synthetic slice is used to
exercise the machinery. What is genuinely demonstrated: the loop is correct
(edited-only signal, retrain, gate), the gate catches real regressions (the
-0.009 was surfaced, not hidden), and the base-size ablation shows targeted
fixes integrate better on a stronger base.

## Exit

A working flywheel: reviewer corrections -> corrected gold -> retrain -> two
eval gates (targeted improvement + no regression) -> deployment decision, with
a base-size ablation. Remaining roadmap: Phase 10 (production + a CI eval-
regression gate that automates exactly this no-regression check), Phase 11
(SaaS).
