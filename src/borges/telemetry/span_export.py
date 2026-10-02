from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

SPAN_KIND_ATTR = "borges.span.kind"


def _hex(value: int, width: int) -> str:
    return format(value, f"0{width}x")


def span_record(span: ReadableSpan) -> dict[str, Any]:
    context = span.get_span_context()
    parent = span.parent
    return {
        "name": span.name,
        "kind": (span.attributes or {}).get(SPAN_KIND_ATTR),
        "trace_id": _hex(context.trace_id, 32),
        "span_id": _hex(context.span_id, 16),
        "parent_span_id": _hex(parent.span_id, 16) if parent is not None else None,
        "start_ns": span.start_time,
        "end_ns": span.end_time,
        "status": span.status.status_code.name,
        "status_description": span.status.description,
        "attributes": {k: v for k, v in (span.attributes or {}).items()},
    }


class SafeExporter(SpanExporter):
    """Wraps any exporter so a failure is counted and swallowed, never raised into a run."""

    def __init__(self, inner: SpanExporter) -> None:
        self.inner = inner
        self.failures = 0
        self.exported = 0

    def export(self, spans: Any) -> SpanExportResult:
        try:
            result = self.inner.export(spans)
        except Exception:
            self.failures += 1
            return SpanExportResult.FAILURE
        if result is SpanExportResult.SUCCESS:
            self.exported += len(spans)
        else:
            self.failures += 1
        return result

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        try:
            return self.inner.force_flush(timeout_millis)
        except Exception:
            self.failures += 1
            return False

    def shutdown(self) -> None:
        try:
            self.inner.shutdown()
        except Exception:
            self.failures += 1


class JsonlSpanExporter(SpanExporter):
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._closed = False

    def export(self, spans: Any) -> SpanExportResult:
        if self._closed:
            return SpanExportResult.FAILURE
        lines = "".join(json.dumps(span_record(s), default=str) + "\n" for s in spans)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(lines)
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def shutdown(self) -> None:
        self._closed = True
