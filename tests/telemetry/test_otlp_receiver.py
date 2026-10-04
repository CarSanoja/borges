from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from borges.config import Settings
from borges.telemetry.exporters import build_sinks


class Receiver(HTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.posts: list[tuple[str, bytes]] = []


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        self.server.posts.append((self.path, self.rfile.read(length)))
        self.send_response(200)
        self.send_header("Content-Type", "application/x-protobuf")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args: object) -> None:
        return None


@pytest.fixture
def receiver() -> Iterator[Receiver]:
    server = Receiver()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def span_names(posts: list[tuple[str, bytes]]) -> list[str]:
    names: list[str] = []
    for _, body in posts:
        request = ExportTraceServiceRequest()
        request.ParseFromString(body)
        for resource in request.resource_spans:
            for scope in resource.scope_spans:
                names.extend(span.name for span in scope.spans)
    return names


def test_spans_reach_a_local_otlp_receiver(
    receiver: Receiver, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = receiver.server_address[1]
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", f"http://127.0.0.1:{port}")
    settings = Settings(_env_file=None)
    sinks = build_sinks(settings, tmp_path)
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    for sink in sinks:
        provider.add_span_processor(sink.processor)
    with provider.get_tracer("borges-test").start_as_current_span("exported-probe"):
        pass
    provider.force_flush()
    provider.shutdown()
    assert [path for path, _ in receiver.posts] == ["/v1/traces"]
    assert span_names(receiver.posts) == ["exported-probe"]
    assert "exported-probe" in (tmp_path / "spans.jsonl").read_text()


def test_no_endpoint_means_nothing_is_posted(
    receiver: Receiver, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    sinks = build_sinks(Settings(_env_file=None), tmp_path)
    provider = TracerProvider()
    for sink in sinks:
        provider.add_span_processor(sink.processor)
    with provider.get_tracer("borges-test").start_as_current_span("local-only"):
        pass
    provider.force_flush()
    provider.shutdown()
    assert receiver.posts == []
