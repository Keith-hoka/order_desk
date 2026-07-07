# Phase 4.5 — confidence calibration (val split)

Isotonic calibrator fit on 6240 (confidence, correct) pairs from the
val split's gold-bearing records, scored with the fine-tuned adapter
(qwen3-4b-sft-full-r8) via the vLLM endpoint, xgrammar-constrained. Val only
-- never test. "Correct" uses the headline's norm_text equality.

## Summary

- Pairs: 6240, overall field accuracy: 0.9925
- **ECE before calibration: 0.0077**
- **ECE after calibration (in-sample): 0.0000**

The after-ECE is **in-sample** -- the isotonic calibrator is fit and
evaluated on the same 6240 pairs, so a 0.0000 gap is expected and overstates
real calibration quality (2004 knots over x in [0.50, 1.0] is near-perfect
memorization). A held-out or cross-validated ECE would be the honest measure
of generalization; the calibrator artifact is still the val-learned mapping,
just not evaluated out-of-sample here. Given how low the before-ECE already
is (0.0077), calibration's practical payoff is diagnostic, not a large ECE
reduction.

## The xgrammar confidence problem, quantified

Raw confidence under xgrammar piles near 1.0, so most fields fall in the top
bin. The binned table below shows the actual distribution -- if nearly all
mass sits in the 0.9-1.0 bin, the raw scores carry little triage signal, and
the calibrator's job is to map that narrow high interval to its true
correctness rate rather than to spread a well-distributed score.

### Before calibration

| bin | range | count | mean conf | accuracy | gap |
|---|---|---|---|---|---|
| 4 | 0.4-0.5 | 1 | 0.4999 | 1.0000 | 0.5001 |
| 5 | 0.5-0.6 | 2 | 0.5622 | 1.0000 | 0.4378 |
| 6 | 0.6-0.7 | 4 | 0.6366 | 1.0000 | 0.3634 |
| 7 | 0.7-0.8 | 5 | 0.7772 | 1.0000 | 0.2228 |
| 8 | 0.8-0.9 | 5 | 0.8825 | 0.4000 | 0.4825 |
| 9 | 0.9-1.0 | 6223 | 0.9996 | 0.9929 | 0.0067 |

### After calibration

| bin | range | count | mean conf | accuracy | gap |
|---|---|---|---|---|---|
| 6 | 0.6-0.7 | 52 | 0.6538 | 0.6538 | 0.0000 |
| 7 | 0.7-0.8 | 10 | 0.7000 | 0.7000 | 0.0000 |
| 8 | 0.8-0.9 | 41 | 0.8537 | 0.8537 | 0.0000 |
| 9 | 0.9-1.0 | 6137 | 0.9967 | 0.9967 | 0.0000 |

## Interpretation

The calibrator is a monotonic map from raw confidence to empirical
correctness, saved as sorted knots (results/calibration/calibrator.json) and loadable at serving
time with pure-Python interpolation (no sklearn dependency in the service).
It is not wired into /extract in this phase -- that is an optional follow-up;
here it is produced and pinned as the basis for HITL review prioritization
(Phase 7), where a reviewer should see the lowest-calibrated-confidence
fields first.

## The real signal: the 0.8-0.9 bin

The before-calibration table hides the actual insight in its tails. Of 6240
fields, 6223 sit in the top bin (0.9-1.0) at 99.3% accuracy -- xgrammar
inflation, no triage value. The low bins (0.4-0.8, 12 fields) are all 100%
correct: the model under-reported confidence there, so low raw confidence is
not a useful "likely wrong" flag. The one place raw confidence genuinely
tracks error is **bin 8 (0.8-0.9): 5 fields, accuracy 0.40**. A moderately-
high confidence that is actually wrong 60% of the time is the signal a
reviewer should act on -- not the lowest-confidence fields (which are fine),
but this middling band.

This reframes what calibration and HITL prioritization buy here: under
xgrammar the mass of fields are uniformly high-confidence and correct, and
the actionable uncertainty is a thin band the raw score barely
distinguishes. The calibrator formalizes that band; Phase 7's review UI
should surface calibrated confidence in the 0.8-0.95 range first, where the
model is both unsure and error-prone.

Because the adapter is highly accurate on val and xgrammar inflates
confidence, ECE is modest before calibration; the value is diagnostic --
exposing the distribution and isolating the actionable band -- not a
dramatic ECE reduction.
