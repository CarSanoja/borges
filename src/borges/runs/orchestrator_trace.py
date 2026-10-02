from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry.trace import INVALID_SPAN, Span, Status, StatusCode

from borges.config import Settings
from borges.runs.store import RunStore
from borges.telemetry import hooks
from borges.telemetry.run_telemetry import RunTelemetry

log = logging.getLogger("borges.telemetry")

TelemetryFactory = Callable[[Settings, str, Any], RunTelemetry]


def open_telemetry(
    factory: TelemetryFactory, settings: Settings, store: RunStore, run_id: str
) -> RunTelemetry | None:
    try:
        return factory(settings, run_id, store.runs_dir / run_id)
    except Exception:
        log.warning("tracing unavailable for this run", extra={"run_id": run_id}, exc_info=True)
        return None


@contextmanager
def run_scope(
    telemetry: RunTelemetry | None, store: RunStore, run_id: str, attributes: dict[str, Any]
) -> Iterator[Span]:
    if telemetry is None:
        yield INVALID_SPAN
        return
    with hooks.bound(telemetry), telemetry.span("run", f"run {run_id}", attributes) as span:
        try:
            store.update_meta(run_id, trace_id=telemetry.trace_id)
        except Exception:
            log.warning("could not record the trace id", extra={"run_id": run_id})
        yield span


def mark_outcome(span: Span, status: str) -> None:
    span.set_attribute("borges.run.status", status)
    if status == "failed":
        span.set_status(Status(StatusCode.ERROR, "run failed"))


def close_telemetry(telemetry: RunTelemetry | None, store: RunStore, run_id: str) -> None:
    if telemetry is None:
        return
    try:
        summary = telemetry.close()
        store.update_meta(run_id, telemetry=summary)
    except Exception:
        log.warning("could not close telemetry", extra={"run_id": run_id}, exc_info=True)
