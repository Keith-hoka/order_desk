import json

from fastapi.testclient import TestClient

from order_desk.api.app import create_app
from order_desk.api.config import Settings
from order_desk.extract_client import ExtractionResult, TokenLogprob
from order_desk.schemas import ExtractedOrder


class FakeExtractClient:
    model = "qwen3-4b-sft-full-r8"

    def __init__(self, order: ExtractedOrder, low_field: str | None = None) -> None:
        self.raw = json.dumps(order.model_dump(), ensure_ascii=False)
        self.order = order
        self.low_field = low_field

    def extract(self, subject: str, body: str) -> ExtractionResult:
        tokens = []
        low_needle = None
        if self.low_field:
            low_needle = json.dumps(getattr(self.order, self.low_field), ensure_ascii=False)
        low_span = (-1, -1)
        if low_needle:
            start = self.raw.find(low_needle)
            low_span = (start, start + len(low_needle))
        for i, ch in enumerate(self.raw):
            lp = -3.0 if low_span[0] <= i < low_span[1] else -0.001
            tokens.append(TokenLogprob(token=ch, logprob=lp))
        return ExtractionResult(
            raw=self.raw,
            tokens=tokens,
            input_tokens=100,
            output_tokens=len(tokens),
            latency_s=0.05,
            model="qwen3-4b-sft-full-r8",
        )


def app_with(client) -> TestClient:
    app = create_app(Settings(adapter_model="x", vllm_base_url="", vllm_api_key="EMPTY"))
    app.state.extract_client = client
    return TestClient(app)


ORDER = ExtractedOrder(
    customer_po_text="PO-4472",
    requested_date_text=None,
    delivery_address_text="Botany warehouse",
    buyer_name_text="Dana",
    notes=None,
    line_items=[
        {
            "product_text": "clear tape",
            "quantity": 6,
            "unit_text": "rolls",
            "unit_price_text": None,
            "item_notes": None,
        }
    ],
)


def test_health_ok() -> None:
    client = app_with(FakeExtractClient(ORDER))
    assert client.get("/health").json() == {"status": "ok"}


def test_ready_reflects_backend() -> None:
    ready = app_with(FakeExtractClient(ORDER))
    assert ready.get("/ready").json()["status"] == "ready"
    app = create_app(Settings(adapter_model="x", vllm_base_url="", vllm_api_key="EMPTY"))
    assert TestClient(app).get("/ready").status_code == 503


def test_extract_returns_extraction_confidence_meta() -> None:
    client = app_with(FakeExtractClient(ORDER, low_field="customer_po_text"))
    resp = client.post("/extract", json={"subject": "order", "body": "send clear tape"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["extraction"]["customer_po_text"] == "PO-4472"
    assert data["extraction"]["line_items"][0]["product_text"] == "clear tape"
    assert "customer_po_text" in data["confidence"]
    assert data["confidence"]["customer_po_text"] < 0.2  # the low-logprob field
    assert data["confidence"]["delivery_address_text"] > 0.9
    assert 0 < data["meta"]["overall_confidence"] <= 1.0
    assert data["meta"]["adapter"] == "qwen3-4b-sft-full-r8"


def test_extract_rejects_empty_fields() -> None:
    client = app_with(FakeExtractClient(ORDER))
    assert client.post("/extract", json={"subject": "", "body": "x"}).status_code == 422


def test_extract_503_without_backend() -> None:
    app = create_app(Settings(adapter_model="x", vllm_base_url="", vllm_api_key="EMPTY"))
    resp = TestClient(app).post("/extract", json={"subject": "a", "body": "b"})
    assert resp.status_code == 503
