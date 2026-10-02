from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from borges.gateway.policy_models import BreakerPolicy


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    policy: BreakerPolicy
    clock: Callable[[], float] = time.monotonic
    failures: int = 0
    opened_at: float | None = None
    probing: bool = False

    @property
    def state(self) -> BreakerState:
        if self.opened_at is None:
            return BreakerState.CLOSED
        if self.clock() - self.opened_at >= self.policy.cooldown_s:
            return BreakerState.HALF_OPEN
        return BreakerState.OPEN

    def allow(self) -> bool:
        state = self.state
        if state is BreakerState.CLOSED:
            return True
        if state is BreakerState.HALF_OPEN and not self.probing:
            self.probing = True
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None
        self.probing = False

    def record_failure(self) -> None:
        self.failures += 1
        was_probe = self.probing
        self.probing = False
        if was_probe or self.failures >= self.policy.failure_threshold:
            self.opened_at = self.clock()


class BreakerRegistry:
    def __init__(self, policy: BreakerPolicy, clock: Callable[[], float] = time.monotonic) -> None:
        self._policy = policy
        self._clock = clock
        self._by_model: dict[str, CircuitBreaker] = {}

    def of(self, model: str) -> CircuitBreaker:
        if model not in self._by_model:
            self._by_model[model] = CircuitBreaker(self._policy, self._clock)
        return self._by_model[model]

    def states(self) -> dict[str, str]:
        return {model: breaker.state.value for model, breaker in self._by_model.items()}
