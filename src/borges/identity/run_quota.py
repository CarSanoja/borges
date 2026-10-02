from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import HTTPException

from borges.config import Settings
from borges.identity.principal import Principal

MAX_OWNERS = 5000
NAMED_ACTIVE_FACTOR = 4
SCRIPTED = "scripted"
LIVE = "live"


@dataclass
class _Bucket:
    tokens: float
    stamp: float


@dataclass
class _Owner:
    buckets: dict[str, _Bucket] = field(default_factory=dict)
    runs: set[str] = field(default_factory=set)
    stamp: float = 0.0


class RunQuota:
    """Keeps one anonymous client from holding every run slot or the shared live budget."""

    def __init__(self, settings: Settings, clock: Callable[[], float] = time.monotonic) -> None:
        self._settings = settings
        self._clock = clock
        self._owners: dict[str, _Owner] = {}
        self._lock = threading.Lock()

    @staticmethod
    def owner_key(principal: Principal, client: str) -> str:
        return f"{principal.id}|{client}" if principal.anonymous else principal.id

    def _shape(self, principal: Principal, kind: str) -> tuple[float, float]:
        s = self._settings
        if principal.anonymous:
            per_s = (
                s.borges_anon_runs_per_min / 60
                if kind == SCRIPTED
                else (s.borges_anon_live_runs_per_hour / 3600)
            )
            burst = 6.0 if kind == SCRIPTED else 4.0
            return min(burst, max(1.0, per_s * 3600)), per_s
        return 60.0, 1.0

    def _active_limit(self, principal: Principal) -> int:
        base = self._settings.borges_anon_active_runs
        return base if principal.anonymous else base * NAMED_ACTIVE_FACTOR

    def _prune(self, now: float) -> None:
        if len(self._owners) < MAX_OWNERS:
            return
        idle = [k for k, o in self._owners.items() if not o.runs and now - o.stamp > 3600]
        for key in idle or list(self._owners)[: MAX_OWNERS // 10]:
            del self._owners[key]

    def admit(
        self,
        principal: Principal,
        client: str,
        live: bool,
        is_active: Callable[[str], bool],
    ) -> None:
        kind, key, now = (
            LIVE if live else SCRIPTED,
            self.owner_key(principal, client),
            self._clock(),
        )
        burst, per_s = self._shape(principal, kind)
        with self._lock:
            self._prune(now)
            owner = self._owners.setdefault(key, _Owner(stamp=now))
            owner.runs = {run for run in owner.runs if is_active(run)}
            if len(owner.runs) >= self._active_limit(principal):
                raise _busy(f"{len(owner.runs)} of your runs are still running", 5)
            bucket = owner.buckets.setdefault(kind, _Bucket(burst, now))
            bucket.tokens = min(burst, bucket.tokens + (now - bucket.stamp) * per_s)
            bucket.stamp = now
            if bucket.tokens < 1.0:
                wait = int((1.0 - bucket.tokens) / max(per_s, 1e-9)) + 1
                raise _busy(f"too many {kind} runs started from this address", wait)
            bucket.tokens -= 1.0
            owner.stamp = now

    def record(self, principal: Principal, client: str, run_id: str) -> None:
        with self._lock:
            owner = self._owners.get(self.owner_key(principal, client))
            if owner is not None:
                owner.runs.add(run_id)


def _busy(reason: str, retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=f"Run quota: {reason}; retry in {retry_after}s.",
        headers={"Retry-After": str(retry_after)},
    )
