from __future__ import annotations

import asyncio

import pytest

from borges.gateway.policy_models import RetryPolicy
from borges.gateway.retry import backoff_delay, is_transient

POLICY = RetryPolicy(max_attempts=5, base_delay_s=0.5, max_delay_s=4.0, jitter=0.25)


class Status(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(str(status_code))
        self.status_code = status_code


class APITimeoutError(Exception):
    pass


class RateLimitError(Exception):
    pass


@pytest.mark.parametrize("status", [500, 502, 503, 504, 429, 408])
def test_server_errors_and_throttling_are_transient(status: int) -> None:
    assert is_transient(Status(status))


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_client_errors_are_not_transient(status: int) -> None:
    assert not is_transient(Status(status))


def test_timeouts_and_connection_failures_are_transient() -> None:
    assert is_transient(TimeoutError()) and is_transient(ConnectionResetError())
    assert is_transient(APITimeoutError()) and is_transient(RateLimitError())


def test_logic_errors_and_cancellation_are_not_transient() -> None:
    assert not is_transient(ValueError("bad output"))
    assert not is_transient(asyncio.CancelledError())


def test_response_status_is_read_when_present() -> None:
    error = Exception("x")
    error.response = Status(503)
    assert is_transient(error)


def test_backoff_doubles_up_to_the_ceiling() -> None:
    delays = [backoff_delay(POLICY, n, lambda: 0.0) for n in range(1, 6)]
    assert delays == [0.5, 1.0, 2.0, 4.0, 4.0]


def test_jitter_only_shortens_within_its_fraction() -> None:
    assert backoff_delay(POLICY, 2, lambda: 1.0) == pytest.approx(1.0 * 0.75)
    for sample in (0.0, 0.3, 0.99):
        assert 0.75 <= backoff_delay(POLICY, 2, lambda s=sample: s) <= 1.0
