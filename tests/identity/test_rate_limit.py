from __future__ import annotations

from borges.config import Settings
from borges.identity.principal import ANONYMOUS, Principal
from borges.identity.rate_limit import RateLimiter

NAMED = Principal(id="caller://a", kind="key", scopes=frozenset())


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def build(**overrides) -> tuple[RateLimiter, Clock]:
    clock = Clock()
    settings = Settings(_env_file=None, **overrides)
    return RateLimiter(settings, clock), clock


def test_bucket_empties_then_refills() -> None:
    limiter, clock = build(borges_rate_anon_burst=3, borges_rate_anon_per_s=1.0)
    assert [limiter.take(ANONYMOUS, "1.1.1.1").allowed for _ in range(4)] == [True] * 3 + [False]
    clock.now += 2.0
    assert limiter.take(ANONYMOUS, "1.1.1.1").allowed


def test_denial_reports_a_retry_delay() -> None:
    limiter, _ = build(borges_rate_anon_burst=1, borges_rate_anon_per_s=0.5)
    limiter.take(ANONYMOUS, "c")
    assert limiter.take(ANONYMOUS, "c").retry_after_s == 2.0


def test_anonymous_buckets_are_per_client() -> None:
    limiter, _ = build(borges_rate_anon_burst=1)
    assert limiter.take(ANONYMOUS, "a").allowed
    assert not limiter.take(ANONYMOUS, "a").allowed
    assert limiter.take(ANONYMOUS, "b").allowed


def test_named_principals_share_one_bucket_across_clients() -> None:
    limiter, _ = build(borges_rate_key_burst=2, borges_rate_anon_burst=1)
    assert limiter.take(NAMED, "x").allowed
    assert limiter.take(NAMED, "y").allowed
    assert not limiter.take(NAMED, "z").allowed


def test_peek_does_not_spend() -> None:
    limiter, _ = build(borges_rate_anon_burst=5)
    assert limiter.peek(ANONYMOUS, "c").remaining == 5
    limiter.take(ANONYMOUS, "c")
    assert limiter.peek(ANONYMOUS, "c").remaining == 4
    assert limiter.peek(ANONYMOUS, "c").remaining == 4
