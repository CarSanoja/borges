from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_INSIDE: ContextVar[bool] = ContextVar("borges_inside_gateway", default=False)


def inside_gateway() -> bool:
    return _INSIDE.get()


@contextmanager
def gateway_call() -> Iterator[None]:
    token = _INSIDE.set(True)
    try:
        yield
    finally:
        _INSIDE.reset(token)
