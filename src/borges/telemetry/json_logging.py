from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import IO

from opentelemetry import trace

HANDLER_MARK = "_borges_json_handler"
RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            payload["trace_id"] = format(context.trace_id, "032x")
            payload["span_id"] = format(context.span_id, "016x")
        for name, value in record.__dict__.items():
            if name not in RESERVED and not name.startswith("_"):
                payload[name] = value
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: int | str = logging.INFO, stream: IO[str] | None = None) -> None:
    root = logging.getLogger()
    for handler in root.handlers:
        if getattr(handler, HANDLER_MARK, False):
            handler.setLevel(level)
            root.setLevel(level)
            return
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter())
    setattr(handler, HANDLER_MARK, True)
    root.addHandler(handler)
    root.setLevel(level)
