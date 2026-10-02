from __future__ import annotations

import json
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from borges.telemetry.span_export import JsonlSpanExporter, SafeExporter


class Exploding(SpanExporter):
    def export(self, spans):
        raise RuntimeError("collector down")

    def shutdown(self) -> None:
        raise RuntimeError("collector down")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        raise RuntimeError("collector down")


class Refusing(SpanExporter):
    def export(self, spans):
        return SpanExportResult.FAILURE


def emit_one(exporter: SpanExporter) -> None:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    with provider.get_tracer("t").start_as_current_span("x"):
        pass


def test_safe_exporter_swallows_and_counts_exceptions() -> None:
    safe = SafeExporter(Exploding())
    emit_one(safe)
    assert safe.failures == 1
    assert safe.force_flush() is False
    safe.shutdown()
    assert safe.failures == 3


def test_safe_exporter_counts_failure_results() -> None:
    safe = SafeExporter(Refusing())
    emit_one(safe)
    assert safe.failures == 1 and safe.exported == 0


def test_jsonl_exporter_writes_one_record_per_span(tmp_path: Path) -> None:
    path = tmp_path / "run" / "spans.jsonl"
    safe = SafeExporter(JsonlSpanExporter(path))
    emit_one(safe)
    record = json.loads(path.read_text().splitlines()[0])
    assert record["name"] == "x" and record["parent_span_id"] is None
    assert len(record["trace_id"]) == 32 and len(record["span_id"]) == 16
    assert safe.exported == 1
