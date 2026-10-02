from __future__ import annotations

from borges.gateway.breaker import BreakerRegistry, BreakerState, CircuitBreaker
from borges.gateway.policy_models import BreakerPolicy

from .conftest import Clock


def breaker(clock: Clock, threshold: int = 3, cooldown: float = 30.0) -> CircuitBreaker:
    return CircuitBreaker(BreakerPolicy(failure_threshold=threshold, cooldown_s=cooldown), clock)


def test_opens_after_the_threshold_and_refuses(clock: Clock) -> None:
    cb = breaker(clock)
    for _ in range(2):
        cb.record_failure()
        assert cb.state is BreakerState.CLOSED and cb.allow()
    cb.record_failure()
    assert cb.state is BreakerState.OPEN and not cb.allow()


def test_success_resets_the_failure_count(clock: Clock) -> None:
    cb = breaker(clock)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    assert cb.state is BreakerState.CLOSED


def test_half_open_after_cooldown_lets_one_probe_through(clock: Clock) -> None:
    cb = breaker(clock)
    for _ in range(3):
        cb.record_failure()
    clock.now += 31
    assert cb.state is BreakerState.HALF_OPEN
    assert cb.allow() and not cb.allow()


def test_successful_probe_closes_the_breaker(clock: Clock) -> None:
    cb = breaker(clock)
    for _ in range(3):
        cb.record_failure()
    clock.now += 31
    assert cb.allow()
    cb.record_success()
    assert cb.state is BreakerState.CLOSED and cb.allow() and cb.allow()


def test_failed_probe_reopens_for_a_full_cooldown(clock: Clock) -> None:
    cb = breaker(clock)
    for _ in range(3):
        cb.record_failure()
    clock.now += 31
    assert cb.allow()
    cb.record_failure()
    assert cb.state is BreakerState.OPEN
    clock.now += 29
    assert not cb.allow()
    clock.now += 2
    assert cb.state is BreakerState.HALF_OPEN


def test_registry_keeps_one_breaker_per_model(clock: Clock) -> None:
    registry = BreakerRegistry(BreakerPolicy(failure_threshold=1, cooldown_s=5), clock)
    registry.of("a").record_failure()
    assert registry.of("a").state is BreakerState.OPEN
    assert registry.of("b").state is BreakerState.CLOSED
    assert registry.states() == {"a": "open", "b": "closed"}
