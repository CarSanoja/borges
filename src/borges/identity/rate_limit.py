from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from borges.config import Settings
from borges.identity.principal import Principal

MAX_BUCKETS = 10_000


@dataclass(frozen=True)
class RateState:
    limit: int
    remaining: int
    refill_per_s: float
    retry_after_s: float
    allowed: bool


@dataclass
class _Bucket:
    tokens: float
    stamp: float


class RateLimiter:
    """Token bucket per principal; anonymous callers get a stricter bucket per client address."""

    def __init__(self, settings: Settings, clock: Callable[[], float] = time.monotonic) -> None:
        self._settings = settings
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _shape(self, principal: Principal) -> tuple[int, float]:
        if principal.anonymous:
            return self._settings.borges_rate_anon_burst, self._settings.borges_rate_anon_per_s
        return self._settings.borges_rate_key_burst, self._settings.borges_rate_key_per_s

    @staticmethod
    def bucket_key(principal: Principal, client: str) -> str:
        return f"{principal.id}|{client}" if principal.anonymous else principal.id

    def _refill(self, bucket: _Bucket, burst: int, rate: float, now: float) -> None:
        bucket.tokens = min(float(burst), bucket.tokens + (now - bucket.stamp) * rate)
        bucket.stamp = now

    def _prune(self, now: float) -> None:
        if len(self._buckets) < MAX_BUCKETS:
            return
        idle = [k for k, b in self._buckets.items() if now - b.stamp > 60]
        for key in idle or list(self._buckets)[: MAX_BUCKETS // 10]:
            del self._buckets[key]

    def take(self, principal: Principal, client: str) -> RateState:
        burst, rate = self._shape(principal)
        key, now = self.bucket_key(principal, client), self._clock()
        with self._lock:
            self._prune(now)
            bucket = self._buckets.setdefault(key, _Bucket(float(burst), now))
            self._refill(bucket, burst, rate, now)
            allowed = bucket.tokens >= 1.0
            if allowed:
                bucket.tokens -= 1.0
            wait = 0.0 if allowed else (1.0 - bucket.tokens) / max(rate, 1e-9)
            return RateState(burst, int(bucket.tokens), rate, round(wait, 3), allowed)

    def peek(self, principal: Principal, client: str) -> RateState:
        burst, rate = self._shape(principal)
        key, now = self.bucket_key(principal, client), self._clock()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                return RateState(burst, burst, rate, 0.0, True)
            self._refill(bucket, burst, rate, now)
            return RateState(burst, int(bucket.tokens), rate, 0.0, bucket.tokens >= 1.0)
