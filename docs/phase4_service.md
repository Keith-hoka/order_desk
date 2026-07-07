# Phase 4 — extraction service (skeleton through Docker)

The fine-tuned adapter (qwen3-4b-sft-full-r8) wrapped as a production
inference service: a FastAPI `/extract` endpoint that is the HTTP wrapper
around the one learned node, surrounded by thin deterministic concerns.
Extraction-only by design — classification and routing are Phase 5; upstream
decides whether to call `/extract`.

## Architecture

- **FastAPI** (`src/order_desk/api/`): `create_app` factory, injectable
  backend via `app.state`. Endpoints: `/extract` (guarded), `/health`,
  `/ready` (open, for infra probes).
- **Backend**: the service does not load the model; it calls the remote
  Modal vLLM+LoRA endpoint over HTTP (`VLLMExtractClient`, logprobs on,
  xgrammar constrained). Serving and API scale independently.
- **Auth** (`auth.py`): JWT bearer, HS256, minimal claims (sub/exp/iat),
  secret-gated (unset `JWT_SECRET` disables auth for dev only; production
  requires a >=32-byte secret). Guards `/extract`; probes stay open.
- **Rate limiting** (`rate_limit.py`): fixed-window counter, Redis in
  production / in-memory for tests, keyed by JWT sub (IP fallback). 429 +
  Retry-After past the limit. Config-gated on `REDIS_URL`.
- **Observability** (`tracing.py`): optional Langfuse behind a Tracer
  protocol; no-op when unconfigured. Records the semantic payload (input,
  extraction, per-field confidence, adapter, latency, repair flag).
- **Per-field confidence** (`confidence.py`): token logprobs aligned to
  field values by character span, aggregated as geometric mean
  (exp(mean(logprob))). Reconstructed-text == raw invariant holds after
  filtering special tokens; BPE alignment verified exact against the live
  endpoint.
- **Packaging**: multi-stage Dockerfile (uv, non-root), docker-compose
  (api + redis). Langfuse via cloud/no-op (self-host needs Postgres +
  Clickhouse, too heavy); vLLM is the remote Modal endpoint, not a compose
  service.

## End-to-end verified (docker compose up)

A live `/extract` through the container returned a well-formed response:
extraction correct (PO, address, buyer, line item verbatim), per-field
confidence present, meta complete (adapter qwen3-4b-sft-full-r8, latency
~2.7s incl. Modal round-trip). Auth enforced (401 without token, 200 with),
rate-limit counting confirmed in Redis, trace no-op without error.

## Confidence under xgrammar — the calibration motivation

Live confidences land at 0.9997-1.0 across nearly all fields. This is the
decision-3a effect: xgrammar prunes the token distribution, so logprobs sit
near zero and confidence piles at 1.0 with almost no discrimination. Raw
confidence is therefore not directly useful for triage; ECE calibration
(Phase 4.5, on the val split, never test) is what turns it into a meaningful
"probability correct." The address field's 0.9997 (vs 1.0 elsewhere) is the
only signal the raw scores leak.

## Ops notes (real deployment gotchas, recorded)

1. **`docker compose restart` does not re-read env_file.** After editing
   `.env`, a `restart` keeps the container's original environment; use
   `up --force-recreate` (or `down && up`) to reload. Cost a debugging loop
   where the container held a stale VLLM_API_KEY while `.env` had the new one.
2. **Modal warm containers hold the old secret.** Rotating a secret and
   redeploying does not restart a running container (the secret is injected
   at container start). Force a cold start with `modal app stop` + redeploy
   so the new container picks up the new secret.

## Exit

`docker compose up` yields a working service; `/extract` returns calibrated-
pending confidence with auth and rate-limiting enforced. Remaining: Phase 4.5
ECE calibration (val split, calibrator artifact, ECE before/after report).
