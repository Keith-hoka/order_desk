"""OpenAI adapter for the baseline runner (step 2.3).

Locked decisions:
- Both stages run through structured outputs with strict json_schema. The
  classify stage wraps the 5-label enum in a one-field envelope (OpenAI
  requires an object root); the adapter unwraps {"label": X} and returns X
  as StageResult.raw -- the envelope is wire packaging, not model content.
  When unwrapping fails, the content passes through untouched and the
  harness brands it invalid; the adapter never guesses.
- The extraction wire schema is derived from the live pydantic schema
  (snapshot-pinned, so it equals the committed contract) minus a documented
  keyword strip: minLength and minimum are removed because strict-mode
  keyword support has shifted across API versions and losing them costs
  nothing -- our own strict pydantic parse stays the final judge; the wire
  schema is guidance, not the verdict.
- temperature 0, best-effort seed, per-stage completion-token caps, SDK
  retries for transient failures. The resolved (dated) model string from
  every response is collected so reports pin the snapshot behind the alias.
"""

from __future__ import annotations

import json
import time
from typing import Any

from order_desk.baseline import Stage, StageResult
from order_desk.schemas import EmailClass, ExtractedOrder

STRIPPED_KEYWORDS = frozenset({"minLength", "minimum"})
MAX_COMPLETION_TOKENS: dict[str, int] = {"classify": 20, "extract": 1500}
DEFAULT_SEED = 20260709


def strip_keywords(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: strip_keywords(v) for k, v in node.items() if k not in STRIPPED_KEYWORDS}
    if isinstance(node, list):
        return [strip_keywords(v) for v in node]
    return node


def wire_extraction_schema() -> dict[str, Any]:
    return strip_keywords(ExtractedOrder.model_json_schema())


def classify_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": [member.value for member in EmailClass]}
        },
        "required": ["label"],
        "additionalProperties": False,
    }


def _unwrap_label(content: str) -> str:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return content
    label = payload.get("label") if isinstance(payload, dict) else None
    return label if isinstance(label, str) else content


class OpenAIBaselineClient:
    def __init__(self, model: str, client: Any | None = None, seed: int = DEFAULT_SEED) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(max_retries=5, timeout=60.0)
        self.model = model
        self.seed = seed
        self._client = client
        self.resolved_models: set[str] = set()

    def _response_format(self, stage: Stage) -> dict[str, Any]:
        if stage == "classify":
            name, schema = "email_class", classify_schema()
        else:
            name, schema = "extracted_order", wire_extraction_schema()
        return {
            "type": "json_schema",
            "json_schema": {"name": name, "strict": True, "schema": schema},
        }

    def run_stage(self, stage: Stage, system: str, user: str, record_id: str) -> StageResult:
        started = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            seed=self.seed,
            max_completion_tokens=MAX_COMPLETION_TOKENS[stage],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=self._response_format(stage),
        )
        latency = time.perf_counter() - started
        self.resolved_models.add(response.model)
        content = response.choices[0].message.content or ""
        raw = _unwrap_label(content) if stage == "classify" else content
        usage = response.usage
        return StageResult(
            raw=raw,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_s=latency,
        )
