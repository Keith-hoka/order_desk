# Corpus notes — synthetic v1

Honest ledger of known quirks, deliberate simplifications, and the realism
posture of the synthetic corpus. Read with SPEC §7 and
data/corpus/MANIFEST.json (measured duplicate rates live there, not here).

## Quirk ledger (recorded, deliberately unfixed; adjudicated in step 1.8)
- (a) Singular canonical unit words: "20 roll of packing paper", "half a
  dozen pack strap clips". Real POs do contain "25 each"-style phrasing;
  whether the singular family reads as realistic is a human-audit call.
- (b) Item-note/product mismatches: notes are sampled globally without
  category awareness ("brown is fine if clear is out" on corner boards).
- (c) Unsigned personal-mailbox emails end at a bare sign-off ("Regards,"
  with no name). Defensible pre-Phase-6; corporate footers will wrap these
  bodies later. Re-check then.
- (d) Quirk (a)'s family extends into amendment glue ("add 216 roll of ...").

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
