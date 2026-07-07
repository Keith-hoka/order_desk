# Phase 4 milestone — production inference service

The fine-tuned adapter (qwen3-4b-sft-full-r8, which beats gpt-4o-mini on both
synthetic and human OOD) wrapped as a production service: a FastAPI /extract
endpoint that is the HTTP surface of the one learned node, surrounded by thin
deterministic concerns. Extraction-only by design; classification and routing
are Phase 5.

## What was built (4.1-4.5)

| step | component | verification |
|---|---|---|
| 4.1 | FastAPI /extract, logprobs client, per-field confidence | offline + live smoke (BPE alignment exact) |
| 4.2 | JWT bearer auth (HS256, secret-gated) | offline; 401/200 enforced in Docker |
| 4.3 | fixed-window rate limit (Redis, per-sub) | offline + Redis counting confirmed live |
| 4.4 | optional Langfuse tracing + Docker Compose | end-to-end via `docker compose up` |
| 4.5 | ECE + isotonic confidence calibration | offline (known-answer pins) + val-split fit |

Test count: 187 passing. All logic offline-testable via injectable fakes;
only smokes and calibration collection touch the network.

## Architecture

The service does not load the model -- it calls the remote Modal vLLM+LoRA
endpoint over HTTP (logprobs on, xgrammar constrained), so serving and API
scale independently. Auth guards /extract; /health and /ready stay open for
probes. Rate limiting keys on the JWT sub. Langfuse is optional (no-op when
unconfigured; self-host omitted as too heavy). Docker Compose runs api +
redis; the vLLM backend is remote.

## Per-field confidence and calibration

Confidence is the geometric mean of token probabilities over each field's
character span. Under xgrammar the token distribution is pruned, so logprobs
sit near zero and confidence piles at ~1.0 -- live /extract returns 0.9997-
1.0 across nearly all fields. Calibration on the val split (never test)
quantified this: of 6240 fields, 6223 sit in the top confidence bin at 99.3%
accuracy. ECE before calibration is already low (0.0077) because the adapter
is highly accurate and both confidence and accuracy hug 1.0.

The actionable finding is not the ECE number but the 0.8-0.9 confidence band:
5 fields there, 40% accurate -- moderately-high confidence that is actually
wrong most of the time. That thin band, not the lowest-confidence fields
(which are all correct), is what HITL review (Phase 7) should surface first.
The isotonic calibrator is pinned as the val-learned confidence->correctness
map; its after-ECE (0.0000) is in-sample and overstates generalization, noted
honestly.

## End-to-end proof

A live `/extract` through the container returned a well-formed response:
extraction correct and verbatim, per-field confidence present, meta complete
(adapter qwen3-4b-sft-full-r8, ~2.7s latency incl. Modal round-trip), with
auth enforced and rate-limit counting confirmed in Redis.

## Ops notes (real deployment gotchas)

- `docker compose restart` does not re-read env_file; use `up --force-recreate`.
- Modal warm containers hold the old secret; rotate with `app stop` + redeploy.

## Exit

A working, Docker-packaged, authenticated, rate-limited extraction service
with traced requests and a pinned confidence calibrator. Remaining phases:
5 (LangGraph orchestration + routing), 6 (real email ingest), 7 (exception-
queue UI consuming per-field confidence), onward.
