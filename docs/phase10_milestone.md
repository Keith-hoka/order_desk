# Phase 10 milestone — CI eval-regression gate (v2)

Phase 9's Gate 2 was a manual judgement: retrain, run the frozen eval, and
check the candidate adapter did not drop F1 below the baseline. Phase 10
automates that judgement in CI. Every push now runs a gate that reads the
committed eval reports and fails the build if a candidate adapter has regressed
headline F1 beyond tolerance on any frozen source. The no-regression decision
is no longer something a human remembers to do -- it is enforced.

## The design split: expensive eval offline, cheap judgement in CI

Running an adapter over the frozen eval needs a GPU, a served endpoint, a
secret, and minutes of inference -- it cannot run on every commit. But the
*pass/fail judgement* is cheap: read two numbers, compare, apply a tolerance.
So the two are split. Eval runs offline (locally or in a dedicated run) and its
reports are committed to the repo as the source of truth. CI reads those
reports and renders the verdict. This mirrors how production ML systems gate on
evals: full evaluation lives in a scheduled or release pipeline, while CI
checks that the committed results clear the bar.

## The gate

`flywheel/regression.py` reads the adapter registry's machine-readable gate
config -- a baseline adapter, a candidate adapter, a tolerance, and, per frozen
source (synthetic, human OOD), the report filenames to compare. It reads
headline F1 from each committed report and marks a source regressed when the
candidate falls below `baseline - tolerance`. Any regressed source fails the
gate. `scripts/check_regression.py` prints the table and exits non-zero on
failure, so CI blocks the change:

source        baseline   candidate     delta
synthetic       0.9978      0.9972   -0.0006      ok
human           0.9508      0.9418   -0.0090      ok
gate: PASS

The human OOD line is exactly Phase 9's surfaced tradeoff: a real -0.009 drop,
within the 0.01 tolerance, so the gate passes -- but a larger regression would
now fail the build automatically rather than relying on someone to notice.

## Reports are the source of truth

The gate reads `results/reports/*.json`. `results/` is gitignored (most reports
and predictions are intermediate), so the four reports the gate depends on
(base and flywheel, synthetic and human) are committed explicitly -- they are
the gate's inputs and must travel with the code. A change that ships a new
candidate adapter updates the registry's candidate and commits its reports; the
gate then compares them against the baseline on the next run.

## What this is and isn't

This gate does not re-run evaluation -- it does not retrain, serve, or infer. It
enforces that the *committed* eval evidence clears the no-regression bar. The
expensive part (producing the reports) stays a deliberate offline step; the
cheap, deterministic part (the verdict) is automated. That is the right split:
CI stays fast and secret-free, while the no-regression guarantee that Phase 9
established by hand is now enforced on every push.

## v2

Phase 10 makes the flywheel's safety guarantee continuous: the loop from Phase 9
(corrections -> retrain -> gates -> deploy) now has its no-regression gate wired
into CI, so no adapter change can silently ship a frozen-eval regression beyond
tolerance. Tagged v2.0.

Remaining roadmap: Phase 11 (SaaS -- org auth, metering, billing).
