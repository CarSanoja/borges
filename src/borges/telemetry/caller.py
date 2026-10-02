from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Caller:
    principal: str | None = None
    agent: str | None = None
    step_id: str | None = None
    option_id: str | None = None
    universe_id: str | None = None
    token: str | None = field(default=None, repr=False)


_ANONYMOUS = Caller()
_CALLER: ContextVar[Caller | None] = ContextVar("borges_caller", default=None)


def current_caller() -> Caller:
    return _CALLER.get() or _ANONYMOUS


@contextmanager
def calling_as(
    principal: str | None = None,
    agent: str | None = None,
    step_id: str | None = None,
    option_id: str | None = None,
    universe_id: str | None = None,
    token: str | None = None,
) -> Iterator[Caller]:
    fields = {
        "principal": principal,
        "agent": agent,
        "step_id": step_id,
        "option_id": option_id,
        "universe_id": universe_id,
        "token": token,
    }
    merged = replace(current_caller(), **{k: v for k, v in fields.items() if v is not None})
    token = _CALLER.set(merged)
    try:
        yield merged
    finally:
        _CALLER.reset(token)
