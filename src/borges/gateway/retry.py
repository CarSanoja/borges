from __future__ import annotations

import asyncio
import random
from collections.abc import Callable

from borges.gateway.policy_models import RetryPolicy

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


def is_transient(exc: BaseException) -> bool:
    if isinstance(exc, asyncio.CancelledError):
        return False
    if isinstance(exc, TimeoutError | ConnectionError):
        return True
    status = _status_of(exc)
    if status is not None:
        return status >= 500 or status in (408, 429)
    return any(cls.__name__ in TRANSIENT_NAMES for cls in type(exc).__mro__)


def backoff_delay(
    policy: RetryPolicy, attempt: int, rng: Callable[[], float] = random.random
) -> float:
    ceiling = min(policy.max_delay_s, policy.base_delay_s * (2 ** (attempt - 1)))
    return ceiling * (1 - policy.jitter * rng())
