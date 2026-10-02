from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span, Status, StatusCode

from borges.config import Settings
from borges.telemetry.audit_anchor import anchor_config
from borges.telemetry.audit_log import AuditLog, checkpoint
from borges.telemetry.audit_record import Decision
from borges.telemetry.caller import current_caller
from borges.telemetry.exporters import Sink, build_sinks
from borges.telemetry.span_export import SPAN_KIND_ATTR

AUDIT_FILE = "audit.jsonl"
GLOBAL_AUDIT_RELATIVE = Path("audit") / "global.jsonl"
FLUSH_TIMEOUT_MS = 3000


def global_audit_path(settings: Settings) -> Path:
    return Path(settings.borges_home) / GLOBAL_AUDIT_RELATIVE


def global_audit_log(settings: Settings) -> AuditLog:
    path = global_audit_path(settings)
    return AuditLog(path, anchor_config(settings, path))


def anchor_global_audit(settings: Settings) -> None:
    path = global_audit_path(settings)
    try:
        checkpoint(path, anchor_config(settings, path))
    except Exception:
        return


def run_audit_path(settings: Settings, run_id: str) -> Path:
    return Path(settings.borges_runs_dir) / run_id / AUDIT_FILE


def _clean(attributes: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in attributes.items() if isinstance(v, str | int | float | bool)}


class RunTelemetry:
    """One trace and two audit chains (run and global) for a single run."""

    def __init__(
        self,
        run_id: str,
        provider: TracerProvider,
        sinks: list[Sink],
        run_audit: AuditLog,
        global_audit: AuditLog | None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings
        self.run_id = run_id
        self.provider = provider
        self.sinks = sinks
        self.run_audit = run_audit
        self.global_audit = global_audit
        self.tracer = provider.get_tracer("borges")
        self.trace_id: str | None = None

    @classmethod
    def open(
        cls, settings: Settings, run_id: str, run_dir: Path, sinks: list[Sink] | None = None
    ) -> RunTelemetry:
        chosen = sinks if sinks is not None else build_sinks(settings, run_dir)
        provider = TracerProvider(
            resource=Resource.create(
                {"service.name": settings.otel_service_name, "borges.run_id": run_id}
            )
        )
        for sink in chosen:
            provider.add_span_processor(sink.processor)
        return cls(
            run_id,
            provider,
            chosen,
            AuditLog(run_dir / AUDIT_FILE),
            global_audit_log(settings),
            settings,
        )

    @contextmanager
    def span(
        self, kind: str, name: str, attributes: dict[str, Any] | None = None
    ) -> Iterator[Span]:
        parent = otel_context.Context() if kind == "run" else None
        attrs = {SPAN_KIND_ATTR: kind, "borges.run_id": self.run_id, **_clean(attributes or {})}
        with self.tracer.start_as_current_span(
            name,
            context=parent,
            attributes=attrs,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            if kind == "run":
                self.trace_id = format(span.get_span_context().trace_id, "032x")
            try:
                yield span
            except BaseException as exc:
                span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
                raise

    def audit(
        self,
        kind: str,
        *,
        decision: Decision | None = None,
        reason: str | None = None,
        principal: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        context = trace.get_current_span().get_span_context()
        fields: dict[str, Any] = {
            "run_id": self.run_id,
            "trace_id": format(context.trace_id, "032x") if context.is_valid else self.trace_id,
            "span_id": format(context.span_id, "016x") if context.is_valid else None,
            "principal": principal or current_caller().principal,
            "decision": decision,
            "reason": reason,
            "data": data,
        }
        self.run_audit.append(kind, **fields)
        if self.global_audit is not None:
            self.global_audit.append(kind, **fields)

    def close(self) -> dict[str, Any]:
        try:
            self.provider.force_flush(FLUSH_TIMEOUT_MS)
            self.provider.shutdown()
        except Exception:
            pass
        if self.settings is not None and self.global_audit is not None:
            anchor_global_audit(self.settings)
        failures = {sink.name: sink.exporter.failures for sink in self.sinks}
        return {
            "trace_id": self.trace_id,
            "exporters": [sink.name for sink in self.sinks],
            "exporter_failures": sum(failures.values()),
            "audit_failures": self.run_audit.failures
            + (self.global_audit.failures if self.global_audit else 0),
        }
