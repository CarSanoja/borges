from __future__ import annotations

import httpx

from borges.gateway.errors import GatewayUnavailable
from borges.sandbox.backend import SandboxError

MAX_CAUSE_DEPTH = 8
UNAVAILABLE_MARKERS = ("unavailable", "connection", "timed out", "temporar", "502", "503", "504")


SDK_TRANSPORT_ERRORS = frozenset({"APIConnectionError", "APITimeoutError"})


def _from_sdk(error: BaseException) -> bool:
    return type(error).__module__.split(".")[0] == "openai"


class TransientRunError(RuntimeError):
    pass


def _transient_one(error: BaseException) -> bool:
    if isinstance(error, TransientRunError | GatewayUnavailable):
        return True
    if _from_sdk(error):
        status = getattr(error, "status_code", None)
        if status is None:
            return type(error).__name__ in SDK_TRANSPORT_ERRORS
        return status >= 500 or status == 429
    if isinstance(error, httpx.TransportError | httpx.TimeoutException):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code >= 500
    if isinstance(error, ConnectionError | TimeoutError):
        return True
    if isinstance(error, SandboxError):
        text = str(error).lower()
        return any(marker in text for marker in UNAVAILABLE_MARKERS)
    return False


def is_transient(error: BaseException) -> bool:
    seen: set[int] = set()
    current: BaseException | None = error
    for _ in range(MAX_CAUSE_DEPTH):
        if current is None or id(current) in seen:
            return False
        if _transient_one(current):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False
