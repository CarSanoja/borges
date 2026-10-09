from __future__ import annotations

import asyncio
import random
from collections.abc import Callable

from borges.gateway.policy_models import RetryPolicy

MAX_CAUSE_DEPTH = 8
TRANSIENT_NAMES = frozenset(
    {
        "APITimeoutError",
        "APIConnectionError",
        "RateLimitError",
        "InternalServerError",
        "ConnectError",
        "ReadTimeout",
        "ConnectTimeout",
        "RemoteProtocolError",
        "ServiceUnavailable",
    }
)


def _status_of(exc: BaseException) -> int | None:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def _transient_one(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError | ConnectionError):
        return True
    status = _status_of(exc)
    if status is not None:
        return status >= 500 or status in (408, 429)
    return any(cls.__name__ in TRANSIENT_NAMES for cls in type(exc).__mro__)


def is_transient(exc: BaseException) -> bool:
    """The provider wraps the SDK's error in an LLMError raised from it, so the chain of causes
    is read too: a Nebius connection error at 70a6102 failed a bank recording on its first try."""
    if isinstance(exc, asyncio.CancelledError):
        return False
    current: BaseException | None = exc
    for _ in range(MAX_CAUSE_DEPTH):
        if current is None:
            return False
        if _transient_one(current):
            return True
        current = current.__cause__
    return False


def is_model_missing(exc: BaseException) -> bool:
    """A 404 means the provider does not serve the model: Token Factory stopped serving Nemotron
    Ultra on 9 October 2026, and every judge and narrator call failed instead of moving on to the
    next model the policy lists."""
    current: BaseException | None = exc
    for _ in range(MAX_CAUSE_DEPTH):
        if current is None:
            return False
        if _status_of(current) == 404 or type(current).__name__ == "NotFoundError":
            return True
        current = current.__cause__
    return False


def backoff_delay(
    policy: RetryPolicy, attempt: int, rng: Callable[[], float] = random.random
) -> float:
    ceiling = min(policy.max_delay_s, policy.base_delay_s * (2 ** (attempt - 1)))
    return ceiling * (1 - policy.jitter * rng())
