import json
import time

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from order_desk.api.app import create_app
from order_desk.api.auth import ALGORITHM, decode_token, issue_token
from order_desk.api.config import Settings
from order_desk.extract_client import ExtractionResult, TokenLogprob
from order_desk.schemas import ExtractedOrder

SECRET = "test-secret-do-not-use-in-prod"


class FakeExtractClient:
    model = "qwen3-4b-sft-full-r8"

    def __init__(self, order: ExtractedOrder) -> None:
        self.raw = json.dumps(order.model_dump(), ensure_ascii=False)

    def extract(self, subject: str, body: str) -> ExtractionResult:
        tokens = [TokenLogprob(token=ch, logprob=-0.001) for ch in self.raw]
        return ExtractionResult(
            raw=self.raw,
            tokens=tokens,
            input_tokens=100,
            output_tokens=len(tokens),
            latency_s=0.05,
            model="qwen3-4b-sft-full-r8",
        )


ORDER = ExtractedOrder(
    customer_po_text="PO-1",
    requested_date_text=None,
    delivery_address_text=None,
    buyer_name_text=None,
    notes=None,
    line_items=[],
)


def guarded_client(secret: str) -> TestClient:
    app = create_app(
        Settings(
            adapter_model="x",
            vllm_base_url="",
            vllm_api_key="EMPTY",
            jwt_secret=secret,
            redis_url="",
            rate_limit_per_minute=60,
        )
    )
    app.state.extract_client = FakeExtractClient(ORDER)
    return TestClient(app)


def test_issue_and_decode_roundtrip() -> None:
    token = issue_token(SECRET, "client-a")
    principal = decode_token(SECRET, token)
    assert principal.sub == "client-a"


def test_decode_rejects_expired() -> None:
    token = issue_token(SECRET, "client-a", ttl_seconds=-1)
    with pytest.raises(HTTPException) as exc:
        decode_token(SECRET, token)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail


def test_decode_rejects_wrong_secret() -> None:
    token = issue_token(SECRET, "client-a")
    with pytest.raises(HTTPException) as exc:
        decode_token("other-secret", token)
    assert exc.value.status_code == 401


def test_decode_rejects_missing_sub() -> None:
    token = jwt.encode({"iat": int(time.time())}, SECRET, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        decode_token(SECRET, token)
    assert "subject" in exc.value.detail


def test_extract_requires_token_when_secret_set() -> None:
    client = guarded_client(SECRET)
    no_auth = client.post("/extract", json={"subject": "a", "body": "b"})
    assert no_auth.status_code == 401
    token = issue_token(SECRET, "client-a")
    with_auth = client.post(
        "/extract",
        json={"subject": "a", "body": "b"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert with_auth.status_code == 200


def test_extract_rejects_bad_token() -> None:
    client = guarded_client(SECRET)
    resp = client.post(
        "/extract",
        json={"subject": "a", "body": "b"},
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401


def test_auth_disabled_when_no_secret() -> None:
    app = create_app(
        Settings(
            adapter_model="x",
            vllm_base_url="",
            vllm_api_key="EMPTY",
            jwt_secret="",
            redis_url="",
            rate_limit_per_minute=60,
        )
    )
    app.state.extract_client = FakeExtractClient(ORDER)
    client = TestClient(app)
    resp = client.post("/extract", json={"subject": "a", "body": "b"})
    assert resp.status_code == 200  # auth off, no token needed


def test_health_and_ready_are_unauthenticated() -> None:
    client = guarded_client(SECRET)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200  # no token, still reachable
