from __future__ import annotations

import io
import json
import logging

from borges.telemetry.json_logging import configure_logging
from borges.telemetry.run_telemetry import RunTelemetry


def test_lines_are_json_with_trace_and_span_ids(tmp_path) -> None:
    from borges.config import Settings

    stream = io.StringIO()
    root = logging.getLogger()
    before = list(root.handlers)
    configure_logging(stream=stream)
    try:
        log = logging.getLogger("borges.test")
        log.info("outside")
        telemetry = RunTelemetry.open(
            Settings(_env_file=None, borges_home=tmp_path / "h"), "r1", tmp_path / "run"
        )
        with telemetry.span("run", "run r1"):
            log.warning("inside %s", "span", extra={"run_id": "r1"})
        telemetry.close()
        configure_logging(stream=stream)
        assert sum(1 for h in root.handlers if h not in before) == 1
    finally:
        for handler in list(root.handlers):
            if handler not in before:
                root.removeHandler(handler)
    outside, inside = (json.loads(line) for line in stream.getvalue().splitlines())
    assert "trace_id" not in outside and outside["message"] == "outside"
    assert inside["level"] == "WARNING" and inside["message"] == "inside span"
    assert inside["trace_id"] == telemetry.trace_id and len(inside["span_id"]) == 16
    assert inside["run_id"] == "r1" and inside["logger"] == "borges.test"
