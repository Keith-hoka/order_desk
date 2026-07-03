# Frozen test fixlog

data/corpus/test.jsonl (and, from step 1.8, test_human.jsonl) are frozen
evaluation objects. The only legitimate reason to change frozen bytes is a
documented labeling or contract error. Every refreeze must:

1. state what was wrong, with record ids;
2. state why the fix cannot wait for a scheduled corpus version bump;
3. write the log entry here first, then run
   `uv run python scripts/materialize_corpus.py --refreeze --entry "<heading>"`
   -- the materializer refuses --refreeze unless the entry text already
   exists in this file;
4. invalidate every audit verdict whose record bytes changed (reset both
   booleans to null, clear notes) and queue those records for re-audit;
5. commit the regenerated files, updated MANIFEST.json, the reset verdicts,
   and the log entry in the same commit.

Comparisons across a refreeze boundary are invalid unless re-run.

## Log

### Refreeze #1 -- 2026-07-03 -- colour-mismatched item note

1. Wrong: ITEM_NOTES were sampled globally, so the colour note
   "brown is fine if clear is out" landed on colour-less products. Audit verdict: all 7
   unrealistic records were monocausal on it.
2. Why now: pre-baseline window -- no numbers exist to invalidate; from
   Phase 2 onward every result pins to these bytes.
3. Fix: pool-size-preserving swap to "no substitutions please", so the rng stream is
   bit-identical elsewhere. Machine-verified against git history
   (d1395be, sha 7d901aacc89033c1): 85/1000 test records
   changed, all new_order, each new line equal to its old line under pure
   note substitution; all dossier records inside the changed set.
   11 of 120 sampled records reset for re-audit
   (verdict lines [1, 11, 13, 16, 26, 31, 34, 39, 53, 67, 68]); pre-refreeze verdicts preserved at d1395be.
4. Incident: the refreeze was committed in cff8251 without this entry and
   without verdict invalidation. The verification script died on a wrong
   interpreter (python3 instead of uv run python) before any side effect
   ran, and the remaining commands were executed past the dead gate.
   Verification therefore ran post-hoc (this commit); it compares the same
   byte sets and is equally strong. Hardening: --refreeze is now gated on
   --entry text already present in this file (entry-before-refreeze).

