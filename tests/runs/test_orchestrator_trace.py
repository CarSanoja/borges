from __future__ import annotations

from pathlib import Path

from opentelemetry.sdk.trace.export import SpanExporter

from borges.cases.registry import CaseRegistry
from borges.runs.bus import EventBus
from borges.runs.models import RunRequest
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore
from borges.telemetry.audit_verify import verify_chain
from borges.telemetry.exporters import Sink, simple_sink
from borges.telemetry.run_telemetry import RunTelemetry, run_audit_path
from borges.telemetry.span_export import SafeExporter
from tests.telemetry.conftest import make_settings


class Down(SpanExporter):
    def export(self, spans):
        raise ConnectionError("collector unreachable")

    def shutdown(self) -> None:
        raise ConnectionError("collector unreachable")


def orchestrator(tmp_path: Path, factory) -> tuple[RunOrchestrator, RunStore]:
    settings = make_settings(tmp_path)
    store = RunStore(settings.borges_runs_dir)
    return (
        RunOrchestrator(
            settings,
            store,
            EventBus(store),
            CaseRegistry(settings.borges_cases_dir),
            telemetry_factory=factory,
        ),
        store,
    )


async def test_exporter_failure_does_not_break_the_run(tmp_path: Path) -> None:
    down = SafeExporter(Down())

    def factory(settings, run_id, run_dir) -> RunTelemetry:
        sinks: list[Sink] = [simple_sink("otlp", down)]
        return RunTelemetry.open(settings, run_id, run_dir, sinks=sinks)

    runs, store = orchestrator(tmp_path, factory)
    snapshot = await runs.execute("r_down", RunRequest(case_id="checkout_ab", llm="scripted"))
    assert snapshot.status == "completed" and snapshot.flip is not None
    assert snapshot.flip.universe_id == "u_4e00fbb461"
    assert down.failures > 100
    meta = store.meta("r_down")
    assert meta["telemetry"]["exporter_failures"] == down.failures
    assert verify_chain(run_audit_path(runs.settings, "r_down")).ok


async def test_telemetry_that_cannot_open_does_not_break_the_run(tmp_path: Path) -> None:
    def factory(settings, run_id, run_dir):
        raise OSError("disk full")

    runs, store = orchestrator(tmp_path, factory)
    snapshot = await runs.execute(
        "r_none", RunRequest(case_id="checkout_ab", llm="scripted", max_universes=2)
    )
    assert snapshot.status == "completed"
    assert "trace_id" not in store.meta("r_none")
    assert not (store.runs_dir / "r_none" / "spans.jsonl").exists()


async def test_failed_run_marks_the_run_span_as_error(tmp_path: Path) -> None:
    runs, store = orchestrator(tmp_path, RunTelemetry.open)
    snapshot = await runs.execute(
        "r_fail", RunRequest(case_id="checkout_ab", llm="nebius", max_universes=2)
    )
    assert snapshot.status == "failed"
    from borges.telemetry.trace_tree import read_spans

    spans = read_spans(store.runs_dir / "r_fail" / "spans.jsonl")
    root = next(s for s in spans if s["kind"] == "run")
    assert root["status"] == "ERROR" and root["attributes"]["borges.run.status"] == "failed"
    assert store.meta("r_fail")["trace_id"] == root["trace_id"]
