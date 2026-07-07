"""Real classifier and extractor for the pipeline (Phase 5).

PromptedClassifier: gpt-4o-mini with structured outputs over the five-class
enum, reusing the snapshot-pinned classification prompt from Phase 2 (so the
pipeline's classification stays comparable to the baselines). Chosen over the
self-hosted Qwen for its markedly better human-OOD classification accuracy
(0.846 vs 0.646) -- classification is the first gate; a misroute sends the
whole email down the wrong path.

AdapterExtractor: wraps the Phase 4 VLLMExtractClient (the fine-tuned adapter,
the one learned node) and converts its output to (ExtractedOrder, confidence).
On parse failure it returns an empty order and no confidence so the pipeline
does not crash -- the finalize node's policy check surfaces the miss.

Both are injectable and offline-testable with fake clients; only real runs
touch the network.
"""

from __future__ import annotations

import math
from typing import Any

from order_desk.baseline import parse_extraction
from order_desk.confidence import field_confidences
from order_desk.extract_client import VLLMExtractClient
from order_desk.pipeline.policy import Classification
from order_desk.prompts import classification_system_prompt, format_email
from order_desk.schemas import EmailClass, ExtractedOrder

_EMPTY_ORDER = ExtractedOrder(
    customer_po_text=None,
    requested_date_text=None,
    delivery_address_text=None,
    buyer_name_text=None,
    notes=None,
    line_items=[],
)


def _classify_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"label": {"type": "string", "enum": [c.value for c in EmailClass]}},
        "required": ["label"],
        "additionalProperties": False,
    }


class PromptedClassifier:
    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(max_retries=5, timeout=60.0)
        self.model = model
        self._client = client

    def __call__(self, subject: str, body: str) -> Classification:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_completion_tokens=20,
            logprobs=True,
            messages=[
                {"role": "system", "content": classification_system_prompt()},
                {"role": "user", "content": format_email(subject, body)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "email_class",
                    "strict": True,
                    "schema": _classify_schema(),
                },
            },
        )
        choice = response.choices[0]
        import json

        label = json.loads(choice.message.content or "{}").get("label", "other")
        confidence = _label_confidence(choice)
        return Classification(email_class=EmailClass(label), confidence=confidence)


def _label_confidence(choice: Any) -> float:
    """Confidence from the label token logprobs, if present; else 1.0."""
    lp = getattr(choice, "logprobs", None)
    if lp is None or getattr(lp, "content", None) is None or not lp.content:
        return 1.0
    # geometric mean of the emitted token probabilities
    logprobs = [tok.logprob for tok in lp.content]
    return math.exp(sum(logprobs) / len(logprobs)) if logprobs else 1.0


class AdapterExtractor:
    def __init__(self, client: VLLMExtractClient) -> None:
        self._client = client

    def __call__(self, subject: str, body: str) -> tuple[ExtractedOrder, dict[str, float]]:
        result = self._client.extract(subject, body)
        parsed, _ = parse_extraction(result.raw)
        if parsed is None:
            return _EMPTY_ORDER, {}
        confidence = field_confidences(result.raw, result.tokens, parsed)
        return parsed, confidence


def build_production_nodes(
    classifier_model: str,
    adapter_model: str,
    vllm_base_url: str,
    vllm_api_key: str,
) -> tuple[PromptedClassifier, AdapterExtractor]:
    """Wire the real classifier and extractor from configuration."""
    classifier = PromptedClassifier(model=classifier_model)
    extract_client = VLLMExtractClient(adapter_model, vllm_base_url, api_key=vllm_api_key)
    return classifier, AdapterExtractor(extract_client)
