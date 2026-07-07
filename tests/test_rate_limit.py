from order_desk.api.rate_limit import InMemoryCounter, RateLimiter


def test_allows_up_to_limit_then_blocks() -> None:
    limiter = RateLimiter(InMemoryCounter(), limit_per_minute=3)
    now = 1_000_000.0  # fixed instant, same window
    decisions = [limiter.check("client-a", now=now) for _ in range(5)]
    allowed = [d.allowed for d in decisions]
    assert allowed == [True, True, True, False, False]
    assert decisions[0].count == 1
    assert decisions[3].count == 4
    assert decisions[3].limit == 3
    assert decisions[3].retry_after > 0


def test_window_resets() -> None:
    limiter = RateLimiter(InMemoryCounter(), limit_per_minute=2)
    base = 1_000_000.0
    # exhaust window 1
    assert limiter.check("c", now=base).allowed
    assert limiter.check("c", now=base).allowed
    assert not limiter.check("c", now=base).allowed
    # next minute -> fresh window
    assert limiter.check("c", now=base + 60).allowed


def test_identities_are_isolated() -> None:
    limiter = RateLimiter(InMemoryCounter(), limit_per_minute=1)
    now = 1_000_000.0
    assert limiter.check("client-a", now=now).allowed
    assert not limiter.check("client-a", now=now).allowed
    assert limiter.check("client-b", now=now).allowed  # different identity, own budget


def test_retry_after_is_within_window() -> None:
    limiter = RateLimiter(InMemoryCounter(), limit_per_minute=1)
    now = 1_000_030.0  # 30s into a minute window
    limiter.check("c", now=now)
    blocked = limiter.check("c", now=now)
    assert not blocked.allowed
    assert 0 < blocked.retry_after <= 60


def test_redis_counter_calls_incr_and_expire() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.store: dict[str, int] = {}
            self.expires: dict[str, int] = {}

        def incr(self, key: str) -> int:
            self.store[key] = self.store.get(key, 0) + 1
            return self.store[key]

        def expire(self, key: str, seconds: int) -> None:
            self.expires[key] = seconds

    from order_desk.api.rate_limit import RedisCounter

    fake = FakeRedis()
    counter = RedisCounter(fake)
    assert counter.incr_in_window("k", 60) == 1
    assert fake.expires["k"] == 60  # EXPIRE set on first hit
    assert counter.incr_in_window("k", 60) == 2
    assert list(fake.expires.keys()) == ["k"]  # not re-set on subsequent hits


def test_in_memory_counter_expiry() -> None:
    counter = InMemoryCounter()
    # deterministic via monkeypatched-free approach: rely on window_seconds arithmetic
    assert counter.incr_in_window("k", 60) == 1
    assert counter.incr_in_window("k", 60) == 2


# --- API-level tests (limiter wired into a live app) ---
import json  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from order_desk.api.app import create_app  # noqa: E402
from order_desk.api.auth import issue_token  # noqa: E402
from order_desk.api.config import Settings  # noqa: E402
from order_desk.extract_client import ExtractionResult, TokenLogprob  # noqa: E402
from order_desk.schemas import ExtractedOrder  # noqa: E402

_SECRET = "rate-limit-test-secret-32-bytes-long!"
_ORDER = ExtractedOrder(
    customer_po_text="PO-1",
    requested_date_text=None,
    delivery_address_text=None,
    buyer_name_text=None,
    notes=None,
    line_items=[],
)


class _FakeClient:
    model = "adapter"

    def extract(self, subject: str, body: str) -> ExtractionResult:
        raw = json.dumps(_ORDER.model_dump(), ensure_ascii=False)
        return ExtractionResult(
            raw=raw,
            tokens=[TokenLogprob(token=c, logprob=-0.001) for c in raw],
            input_tokens=10,
            output_tokens=len(raw),
            latency_s=0.01,
            model="adapter",
        )


def _limited_app(limit: int, secret: str = _SECRET) -> TestClient:
    app = create_app(
        Settings(
            adapter_model="x",
            vllm_base_url="",
            vllm_api_key="EMPTY",
            jwt_secret=secret,
            redis_url="",
            rate_limit_per_minute=limit,
        )
    )
    app.state.extract_client = _FakeClient()
    app.state.rate_limiter = RateLimiter(InMemoryCounter(), limit_per_minute=limit)
    return TestClient(app)


def _post(client: TestClient, token: str | None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/extract", json={"subject": "a", "body": "b"}, headers=headers)


def test_api_throttles_after_limit() -> None:
    client = _limited_app(limit=2)
    token = issue_token(_SECRET, "client-a")
    assert _post(client, token).status_code == 200
    assert _post(client, token).status_code == 200
    blocked = _post(client, token)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_api_isolates_identities() -> None:
    client = _limited_app(limit=1)
    a, b = issue_token(_SECRET, "a"), issue_token(_SECRET, "b")
    assert _post(client, a).status_code == 200
    assert _post(client, a).status_code == 429
    assert _post(client, b).status_code == 200  # separate budget


def test_api_no_limiter_when_unconfigured() -> None:
    app = create_app(
        Settings(
            adapter_model="x",
            vllm_base_url="",
            vllm_api_key="EMPTY",
            jwt_secret=_SECRET,
            redis_url="",
            rate_limit_per_minute=1,
        )
    )
    app.state.extract_client = _FakeClient()
    # rate_limiter left as None by create_app (redis_url empty)
    client = TestClient(app)
    token = issue_token(_SECRET, "a")
    for _ in range(5):
        assert _post(client, token).status_code == 200  # never throttled


def test_health_not_rate_limited() -> None:
    client = _limited_app(limit=1)
    for _ in range(5):
        assert client.get("/health").status_code == 200
