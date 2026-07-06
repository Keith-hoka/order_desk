"""Logprobs-enabled vLLM client for the extraction service (Phase 4).

Independent of VLLMBaselineClient (the frozen Phase 2/3 baseline interface,
left untouched for reproducibility). This client requests token logprobs so
per-field confidence can be computed, keeps xgrammar constraint on (decision
3a: a single constrained generation), and returns the selected-token
logprobs alongside the raw text.

Confidence semantics under xgrammar are honest but constrained: the grammar
prunes the token distribution, so a logprob is P(token | grammar-legal set),
not the unconstrained model confidence. Where the grammar leaves one legal
token, logprob ~= 0 and exp ~= 1. This inflates confidence; ECE calibration
(step 4.x) measures how much, on the val split, never test.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

from order_desk.openai_client import wire_extraction_schema
from order_desk.prompts import extraction_system_prompt, format_email

MAX_TOKENS = 1500
DEFAULT_SEED = 20260709


@dataclass(frozen=True)
class TokenLogprob:
    token: str
    logprob: float


@dataclass(frozen=True)
class ExtractionResult:
    raw: str
    tokens: list[TokenLogprob]
    input_tokens: int
    output_tokens: int
    latency_s: float
    model: str


class ExtractClient(Protocol):
    def extract(self, subject: str, body: str) -> ExtractionResult: ...


class VLLMExtractClient:
    def __init__(
        self,
        model: str,
        base_url: str,
        *,
        api_key: str = "EMPTY",
        client: Any | None = None,
        seed: int = DEFAULT_SEED,
    ) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(base_url=base_url, api_key=api_key, max_retries=5, timeout=180.0)
        self.model = model
        self.seed = seed
        self._client = client

    def extract(self, subject: str, body: str) -> ExtractionResult:
        started = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            seed=self.seed,
            max_tokens=MAX_TOKENS,
            logprobs=True,
            messages=[
                {"role": "system", "content": extraction_system_prompt()},
                {"role": "user", "content": format_email(subject, body)},
            ],
            extra_body={"guided_json": wire_extraction_schema()},
        )
        latency = time.perf_counter() - started
        choice = response.choices[0]
        content = choice.message.content or ""
        tokens: list[TokenLogprob] = []
        if choice.logprobs is not None and choice.logprobs.content is not None:
            for entry in choice.logprobs.content:
                # Skip special/stop tokens (e.g. <|im_end|>): they carry no value
                # characters and would break the reconstructed-text == raw invariant
                # that char-span confidence alignment relies on.
                token = entry.token
                if token.startswith("<|") and token.endswith("|>"):
                    continue
                tokens.append(TokenLogprob(token=token, logprob=entry.logprob))
        usage = response.usage
        return ExtractionResult(
            raw=content,
            tokens=tokens,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_s=latency,
            model=response.model,
        )
