from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry.trace import Span

from borges.telemetry import hooks
from borges.telemetry.caller import calling_as


@contextmanager
def option_span(kind: str, step_id: str, option_id: str) -> Iterator[Span]:
    attributes = {"borges.step_id": step_id, "borges.option_id": option_id}
    with (
        calling_as(step_id=step_id, option_id=option_id),
        hooks.span(kind, f"{kind} {step_id}.{option_id}", **attributes) as span,
    ):
        yield span


@contextmanager
def universe_span(universe_id: str, kind: str) -> Iterator[Span]:
    attributes = {"borges.universe.id": universe_id, "borges.universe.kind": kind}
    with (
        calling_as(universe_id=universe_id),
        hooks.span("universe", f"universe {universe_id}", **attributes) as span,
    ):
        yield span
