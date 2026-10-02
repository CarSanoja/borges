from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanProcessor,
)

from borges.config import Settings
from borges.telemetry.span_export import JsonlSpanExporter, SafeExporter

SPANS_FILE = "spans.jsonl"
OTLP_TIMEOUT_S = 3


def otlp_traces_endpoint(base: str) -> str:
    trimmed = base.rstrip("/")
    return trimmed if trimmed.endswith("/v1/traces") else f"{trimmed}/v1/traces"


def make_otlp_exporter(endpoint: str) -> SafeExporter:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    return SafeExporter(
        OTLPSpanExporter(endpoint=otlp_traces_endpoint(endpoint), timeout=OTLP_TIMEOUT_S)
    )


@dataclass
class Sink:
    name: str
    exporter: SafeExporter
    processor: SpanProcessor


def simple_sink(name: str, exporter: SafeExporter) -> Sink:
    return Sink(name, exporter, SimpleSpanProcessor(exporter))


def build_sinks(settings: Settings, run_dir: Path) -> list[Sink]:
    sinks = [simple_sink("jsonl", SafeExporter(JsonlSpanExporter(run_dir / SPANS_FILE)))]
    endpoint = settings.otel_exporter_otlp_endpoint
    if endpoint:
        exporter = make_otlp_exporter(endpoint)
        batch = BatchSpanProcessor(
            exporter,
            export_timeout_millis=OTLP_TIMEOUT_S * 1000,
            schedule_delay_millis=1000,
        )
        sinks.append(Sink("otlp", exporter, batch))
    return sinks
