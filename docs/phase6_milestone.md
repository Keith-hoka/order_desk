# Phase 6 milestone — email ingest & standardization

An input-standardization layer in front of the pipeline: real email is RFC
822/MIME (headers, multipart, HTML, signatures, quoted reply chains) while the
pipeline expects a clean (subject, body). This layer parses the message,
chooses a text body, strips noise, preserves threading metadata, and hands the
pipeline the clean input it assumes.

## What was built

- **standardize** (`ingest/standardize.py`): MIME parse (stdlib `email`),
  text/plain preferred else text/html converted (html2text), signature and
  quoted-history stripping, thread metadata (In-Reply-To / References) kept out
  of the body.
- **EmailSource protocol** (`ingest/source.py`): pluggable origin.
  `EmlDirectorySource` reads .eml files; `ImapSource` is an interface stub
  (decision A -- the architecture supports a live mailbox; IMAP transport is a
  replaceable detail, left unimplemented to avoid credentials and preserve
  reproducibility).
- **packing** (`ingest/pack.py`): wraps the human slice as RFC 822 with mixed
  realism -- faithful, signatures, HTML, and a constructed reply that quotes a
  prior question.
- **ingest -> pipeline** (`ingest/run.py`): standardize then run, merging
  standardization asks (reply-history) with pipeline asks (blend).

## Threading: decision A and the reply reality

Order conversations are incremental -- a reply may carry only "72 rolls please"
while the product and PO sit in an earlier message. Blindly stripping quoted
history would leave a partial order; blindly concatenating the whole thread
would drag in stale or off-topic context. Decision A: extraction uses the
latest single message with quoted history removed, and a reply-shaped message
(short body, In-Reply-To present) is flagged with a **reply-history ask**
rather than silently extracted from partial context.

This is honest about a real boundary: the fine-tune was trained on
self-contained single emails and has not seen multi-turn threads, so
cross-message aggregation is surfaced as a reviewable exception, not faked. The
constructed reply case demonstrates it: "72 rolls please, same as last time."
with the quoted question "How many rolls did you need?" stripped -> body is
just the answer, is_reply true, and the reply-history ask fires.

## End-to-end: standardization is lossless on clean content

Offline round-trip tests verify the body is clean; the ingest smoke verifies
the stronger property -- that a clean body feeds the real model to the same
result as the raw body. Five human orders were packed as noisy .eml (some with
signatures/HTML), standardized, and run through the real pipeline; extraction
and routing matched the raw-body path exactly (5/5 lossless). Standardization
strips noise without changing order semantics.

The smoke also reproduced a known failure mode on real .eml: HUM-0003
("...is email the right channel?") is an order classified as inquiry and routed
away from extraction -- the same extract->inquiry confusion Phase 5 measured,
a classification problem the standardization layer correctly does not mask.

## Exit

A standardization layer that turns messy MIME/HTML/signed/threaded email into
the pipeline's clean input, with a pluggable source (eml now, IMAP-ready),
proven lossless end-to-end. Remaining: Phase 7 (exception-queue UI consuming
per-field confidence + blend/history asks), Phase 8 (mock ERP + Slack), onward.
