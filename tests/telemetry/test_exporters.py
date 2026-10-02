from __future__ import annotations

from pathlib import Path

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

from borges.config import Settings
from borges.telemetry.exporters import SPANS_FILE, build_sinks, otlp_traces_endpoint
from borges.telemetry.span_export import JsonlSpanExporter


def test_local_exporter_is_the_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    sinks = build_sinks(Settings(_env_file=None), tmp_path)
    assert [s.name for s in sinks] == ["jsonl"]
    assert isinstance(sinks[0].exporter.inner, JsonlSpanExporter)
    assert sinks[0].exporter.inner.path == tmp_path / SPANS_FILE
    assert isinstance(sinks[0].processor, SimpleSpanProcessor)


def test_otlp_exporter_is_selected_by_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    sinks = build_sinks(Settings(_env_file=None), tmp_path)
    assert [s.name for s in sinks] == ["jsonl", "otlp"]
    otlp = sinks[1]
    assert isinstance(otlp.exporter.inner, OTLPSpanExporter)
    assert otlp.exporter.inner._endpoint == "http://collector:4318/v1/traces"
    assert isinstance(otlp.processor, BatchSpanProcessor)
    otlp.processor.shutdown()


def test_blank_endpoint_counts_as_unset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    assert [s.name for s in build_sinks(Settings(_env_file=None), tmp_path)] == ["jsonl"]


def test_traces_path_is_appended_once() -> None:
    assert otlp_traces_endpoint("http://h:4318/") == "http://h:4318/v1/traces"
    assert otlp_traces_endpoint("http://h:4318/v1/traces") == "http://h:4318/v1/traces"
