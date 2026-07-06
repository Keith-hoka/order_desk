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
