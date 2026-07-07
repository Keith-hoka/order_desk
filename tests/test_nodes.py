import json
from types import SimpleNamespace

from order_desk.extract_client import ExtractionResult, TokenLogprob
from order_desk.pipeline.nodes import AdapterExtractor, PromptedClassifier, _classify_schema
from order_desk.pipeline.policy import Classification
from order_desk.schemas import EmailClass, ExtractedOrder


# --- PromptedClassifier with a fake OpenAI client ---
class _StubChatCompletions:
    def __init__(self, label: str, with_logprobs: bool = True) -> None:
        self.label = label
        self.with_logprobs = with_logprobs
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        logprobs = None
        if self.with_logprobs:
            logprobs = SimpleNamespace(content=[SimpleNamespace(token=self.label, logprob=-0.05)])
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps({"label": self.label})),
                    logprobs=logprobs,
                )
            ]
        )


def _stub_openai(label: str, with_logprobs: bool = True):
    completions = _StubChatCompletions(label, with_logprobs)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def test_classifier_returns_parsed_label() -> None:
    client, completions = _stub_openai("new_order")
    clf = PromptedClassifier(client=client)
    result = clf("order", "send tape")
    assert isinstance(result, Classification)
    assert result.email_class == EmailClass.NEW_ORDER
    assert 0.9 < result.confidence <= 1.0  # exp(-0.05) ~ 0.95
    # request shape
    fmt = completions.kwargs["response_format"]
    assert fmt["json_schema"]["schema"] == _classify_schema()
    assert set(fmt["json_schema"]["schema"]["properties"]["label"]["enum"]) == {
        c.value for c in EmailClass
    }


def test_classifier_confidence_falls_back_without_logprobs() -> None:
    client, _ = _stub_openai("inquiry", with_logprobs=False)
    clf = PromptedClassifier(client=client)
    result = clf("q", "what's your lead time")
    assert result.email_class == EmailClass.INQUIRY
    assert result.confidence == 1.0


def test_classify_schema_covers_all_classes() -> None:
    enum = _classify_schema()["properties"]["label"]["enum"]
    assert set(enum) == {c.value for c in EmailClass}


# --- AdapterExtractor with a fake VLLMExtractClient ---
class _FakeExtractClient:
    def __init__(self, order: ExtractedOrder) -> None:
        self.raw = json.dumps(order.model_dump(), ensure_ascii=False)

    def extract(self, subject: str, body: str) -> ExtractionResult:
        tokens = [TokenLogprob(token=c, logprob=-0.01) for c in self.raw]
        return ExtractionResult(
            raw=self.raw,
            tokens=tokens,
            input_tokens=10,
            output_tokens=len(self.raw),
            latency_s=0.01,
            model="adapter",
        )


class _BadExtractClient:
    def extract(self, subject: str, body: str) -> ExtractionResult:
        return ExtractionResult(
            raw="not json at all",
            tokens=[],
            input_tokens=5,
            output_tokens=4,
            latency_s=0.01,
            model="adapter",
        )


ORDER = ExtractedOrder(
    customer_po_text="PO-1",
    requested_date_text=None,
    delivery_address_text="Botany",
    buyer_name_text=None,
    notes=None,
    line_items=[
        {
            "product_text": "tape",
            "quantity": 6,
            "unit_text": "rolls",
            "unit_price_text": None,
            "item_notes": None,
        }
    ],
)


def test_extractor_returns_order_and_confidence() -> None:
    extractor = AdapterExtractor(_FakeExtractClient(ORDER))
    order, confidence = extractor("s", "b")
    assert order.customer_po_text == "PO-1"
    assert order.line_items[0].product_text == "tape"
    assert "customer_po_text" in confidence
    assert all(0 < c <= 1.0 for c in confidence.values())


def test_extractor_handles_parse_failure() -> None:
    extractor = AdapterExtractor(_BadExtractClient())
    order, confidence = extractor("s", "b")
    assert order.line_items == []  # empty order on parse failure
    assert confidence == {}  # no confidence, pipeline does not crash
