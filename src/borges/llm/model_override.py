from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from borges.llm.client import ModelSpec

_OVERRIDE: ContextVar[ModelSpec | None] = ContextVar("borges_model_override", default=None)


def model_override() -> ModelSpec | None:
    return _OVERRIDE.get()


@contextmanager
def use_model(spec: ModelSpec | None) -> Iterator[None]:
    token = _OVERRIDE.set(spec)
    try:
        yield
    finally:
        _OVERRIDE.reset(token)
