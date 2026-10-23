"""Rate limiter with a fake clock."""

from src.api.ratelimit import RateLimiter, client_id


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now


def test_per_minute_limit_per_client_and_reset():
    clock = Clock()
    limiter = RateLimiter(per_minute=2, per_day=100, clock=clock)
    assert limiter.check("a") is None and limiter.check("a") is None
    assert limiter.check("a") == "too many questions per minute"
    assert limiter.check("b") is None  # other visitors aren't affected
    clock.now += 61
    assert limiter.check("a") is None


def test_daily_limit_for_everyone():
    limiter = RateLimiter(per_minute=10, per_day=2, clock=Clock())
    assert limiter.check("a") is None and limiter.check("b") is None
    assert limiter.check("c") == "daily limit reached"


def test_client_id_uses_first_forwarded_ip():
    assert client_id({"x-forwarded-for": "1.2.3.4, 10.0.0.1"}, "fallback") == "1.2.3.4"
    assert client_id({}, "127.0.0.1") == "127.0.0.1"
    assert client_id({"cf-connecting-ip": "5.6.7.8", "x-forwarded-for": "9.9.9.9"}, "x") == "5.6.7.8"
