"""vLLM adapter for the baseline runner (step 2.4a).

Locked decisions:
- The client speaks the OpenAI-compatible API of a vLLM server via the
  OpenAI SDK pointed at --base-url -- deliberately the same wire shape
  Phase 4 serving will expose. Nothing Modal-specific lives here; a local
  `vllm serve` behaves identically.
- Classification is guided in every variant: extra_body {"guided_choice":
  [the five labels]} -- the ± ablation applies to extraction only (Phase 2
  decision record), and a constrained single choice needs no envelope, so
  raw is the label itself with no unwrapping.
- Extraction has two variants. "xgrammar" passes the same stripped wire
  schema used for the OpenAI adapter as {"guided_json": ...}: the backend
  (xgrammar) is a server-side flag, and wire-constraint parity across
  providers keeps the comparison about models, not schemas. "free" sends no
  constraint, so the deterministic repair path and parse_rate get exercised
  for real.
- max_tokens rather than max_completion_tokens for vLLM compatibility;
  temperature 0; seed passed through; resolved model strings captured from
  responses as with the OpenAI adapter.
"""

from __future__ import annotations

import time
from typing import Any

from order_desk.baseline import Stage, StageResult
from order_desk.openai_client import wire_extraction_schema
from order_desk.schemas import EmailClass

VARIANTS = ("xgrammar", "free")
MAX_TOKENS: dict[str, int] = {"classify": 10, "extract": 1500}
DEFAULT_SEED = 20260709


class VLLMBaselineClient:
    def __init__(
        self,
        model: str,
        base_url: str,
        *,
        variant: str = "xgrammar",
        api_key: str = "EMPTY",
        client: Any | None = None,
        seed: int = DEFAULT_SEED,
    ) -> None:
        if variant not in VARIANTS:
            raise ValueError(f"unknown variant {variant!r}; expected one of {VARIANTS}")
        if client is None:
            from openai import OpenAI

            client = OpenAI(base_url=base_url, api_key=api_key, max_retries=5, timeout=180.0)
        self.model = model
        self.variant = variant
        self.seed = seed
        self._client = client
        self.resolved_models: set[str] = set()

    def _extra_body(self, stage: Stage) -> dict[str, Any]:
        if stage == "classify":
            return {"guided_choice": [member.value for member in EmailClass]}
        if self.variant == "xgrammar":
            return {"guided_json": wire_extraction_schema()}
        return {}

    def run_stage(self, stage: Stage, system: str, user: str, record_id: str) -> StageResult:
        started = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            seed=self.seed,
            max_tokens=MAX_TOKENS[stage],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            extra_body=self._extra_body(stage),
        )
        latency = time.perf_counter() - started
        self.resolved_models.add(response.model)
        content = response.choices[0].message.content or ""
        usage = response.usage
        return StageResult(
            raw=content,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_s=latency,
        )
