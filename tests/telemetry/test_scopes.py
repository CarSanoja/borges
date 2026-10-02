from __future__ import annotations

from pathlib import Path

from borges.config import Settings
from borges.telemetry import hooks
from borges.telemetry.caller import current_caller
from borges.telemetry.run_telemetry import RunTelemetry
from borges.telemetry.scopes import option_span, universe_span
from borges.telemetry.trace_tree import read_spans


def test_scopes_set_caller_and_span_attributes(tmp_path: Path) -> None:
    telemetry = RunTelemetry.open(
        Settings(_env_file=None, borges_home=tmp_path / "h"), "r1", tmp_path / "run"
    )
    with hooks.bound(telemetry), telemetry.span("run", "run r1"):
        with universe_span("u_1", "single"), option_span("step", "s1", "a"):
            caller = current_caller()
            assert (caller.universe_id, caller.step_id, caller.option_id) == ("u_1", "s1", "a")
        assert current_caller().universe_id is None
    telemetry.close()
    spans = {s["kind"]: s for s in read_spans(tmp_path / "run" / "spans.jsonl")}
    assert spans["step"]["parent_span_id"] == spans["universe"]["span_id"]
    assert spans["step"]["attributes"]["borges.option_id"] == "a"
    assert spans["universe"]["attributes"]["borges.universe.kind"] == "single"


def test_scopes_work_without_telemetry() -> None:
    with universe_span("u_1", "single") as span, option_span("step", "s", "o"):
        span.set_attribute("x", 1)
