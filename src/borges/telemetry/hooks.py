from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from opentelemetry.trace import INVALID_SPAN, Span

from borges.telemetry.audit_record import Decision

if TYPE_CHECKING:
    from borges.telemetry.run_telemetry import RunTelemetry

_CURRENT: ContextVar[RunTelemetry | None] = ContextVar("borges_run_telemetry", default=None)


def current() -> RunTelemetry | None:
    return _CURRENT.get()


@contextmanager
def bound(telemetry: RunTelemetry) -> Iterator[RunTelemetry]:
    token = _CURRENT.set(telemetry)
    try:
        yield telemetry
    finally:
        _CURRENT.reset(token)


def span(kind: str, name: str, **attributes: Any):
    telemetry = _CURRENT.get()
    if telemetry is None:
        return nullcontext(INVALID_SPAN)
    return telemetry.span(kind, name, attributes)


def active_span() -> Span:
    from opentelemetry import trace

    return trace.get_current_span()


def audit(
    kind: str,
    *,
    decision: Decision | None = None,
    reason: str | None = None,
    principal: str | None = None,
    **data: Any,
) -> None:
    telemetry = _CURRENT.get()
    if telemetry is None:
        return
    try:
        telemetry.audit(kind, decision=decision, reason=reason, principal=principal, data=data)
    except Exception:
        telemetry.run_audit.failures += 1
