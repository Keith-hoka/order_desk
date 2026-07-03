# Corpus notes — synthetic v1

Honest ledger of known quirks, deliberate simplifications, and the realism
posture of the synthetic corpus. Read with SPEC §7 and
data/corpus/MANIFEST.json (measured duplicate rates live there, not here).

## Quirk ledger (recorded, deliberately unfixed; adjudicated in step 1.8)
- (a) Singular canonical unit words: "20 roll of packing paper", "half a
  dozen pack strap clips". Real POs do contain "25 each"-style phrasing;
  whether the singular family reads as realistic is a human-audit call.
  **Adjudicated (1.8b):** 47/47 tagged fine -- kept as-is.
- (b) Item-note/product mismatches: notes are sampled globally without
  category awareness ("brown is fine if clear is out" on corner boards).
  **Adjudicated (1.8b):** all 7 unrealistic audit records were monocausal on
  the colour note landing on colour-less products; fixed via refreeze #1 --
  a stream-preserving string swap to "no substitutions please" (see
  docs/frozen_test_fixlog.md). The other two notes were judged odd at worst
  and stay global.
- (c) Unsigned personal-mailbox emails end at a bare sign-off ("Regards,"
  with no name). Defensible pre-Phase-6; corporate footers will wrap these
  bodies later. Re-check then.
  **Adjudicated (1.8b):** 14 tagged fine -- kept; the Phase-6 re-check stands.
- (d) Quirk (a)'s family extends into amendment glue ("add 216 roll of ...").
  **Adjudicated (1.8b):** 6/6 tagged fine -- kept.

## v1 simplifications (by design, recorded)
- Amendments: exactly one change per email; change lines carry no noise
  dimensions (no typo / pack-size trap / price); referenced POs are generated
  from the customer's template and deliberately not linked to concrete orders
  elsewhere in the corpus (cross-record references would leak across splits).
- Implicit amendments ("actually make that 50" with no referent) are excluded
  until Phase 6 threading makes them a fair task.
- inquiry/general, other/marketing, and other/misdirected are single-template
  families with low diversity; a classifier may learn the template rather
  than the intent. Their measured cross-split duplicate rates live in
  MANIFEST.json and are expected to be materially nonzero, so classification
  numbers on the synthetic split are in-distribution upper bounds.
- Single corpus timezone (Australia/Sydney), English only, one order per
  email, no attachments processed.

## Oracle conventions surfaced by the audit (recorded, not fixed)

- Bare quantities on pack-size products read as the selling unit
  (TST-SCN-000135: "510 laser labels" -> 510 packs -> above_max, where a
  human may read pieces). Safe under the routing policy -- either reading
  lands in the exception queue -- but the Phase 5 validator should carry a
  pack-ambiguity sub-reason so reviewers are not shown one unit reading as
  settled fact (same principle as the 1.4d denomination gate).
- Trap-line tokenization is a convention (TST-SCN-000442: qty 1000 / unit
  "buckles" / product "strap clips" follows mention grammar). The convention
  is part of the task definition: the schema field descriptions state it and
  every model -- baselines included -- receives those descriptions in the
  prompt. Step 1.9 adds a trap-line slice so any residual convention penalty
  is visible.

## Realism posture
Template-synthetic text puts a ceiling on linguistic diversity. Correction
mechanisms: (1) the human-certified subsample and human-authored OOD slice
(step 1.8, SPEC §7); (2) every headline result is reported on both tracks.
If fine-tuning wins on the synthetic split but collapses on the human slice,
that is template overfitting, and it gets reported as such.

## Deferred diversity levers
- LLM paraphrase augmentation of train only (never test/val), using a model
  family different from any future judge. Candidate for Phase 3 if the data
  scaling curve is still rising at full train size.
- Category-aware item-note pools (restores colour-style notes on the right
  products): bundle with the next scheduled corpus version bump.
