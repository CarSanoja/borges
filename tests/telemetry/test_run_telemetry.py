from __future__ import annotations

from collections import Counter

from borges.telemetry.audit_verify import verify_chain
from borges.telemetry.run_telemetry import global_audit_path
from borges.telemetry.trace_tree import read_spans
from tests.telemetry.conftest import ScriptedRun


def test_one_trace_per_run_recorded_in_meta_and_started_event(scripted_run: ScriptedRun) -> None:
    spans = read_spans(scripted_run.run_dir / "spans.jsonl")
    assert {s["trace_id"] for s in spans} == {
        scripted_run.store.meta(scripted_run.run_id)["trace_id"]
    }
    started = scripted_run.store.events(scripted_run.run_id)[0]
    assert started.type == "run.started"
    assert started.data["trace_id"] == spans[0]["trace_id"]
    telemetry = scripted_run.store.meta(scripted_run.run_id)["telemetry"]
    assert telemetry["exporters"] == ["jsonl"] and telemetry["exporter_failures"] == 0


def test_span_tree_has_the_expected_shape(scripted_run: ScriptedRun) -> None:
    spans = read_spans(scripted_run.run_dir / "spans.jsonl")
    by_id = {s["span_id"]: s for s in spans}
    kinds = Counter(s["kind"] for s in spans)
    assert kinds["run"] == 1 and kinds["universe"] == 7 and kinds["model_call"] >= 20
    assert kinds["stage"] == 8
    assert kinds["option.code"] == kinds["option.smoke"] == 10
    assert kinds["sandbox_exec"] > 0 and kinds["step"] > 0

    def parent_kind(span: dict) -> str | None:
        parent = by_id.get(span["parent_span_id"])
        return parent["kind"] if parent else None

    root = next(s for s in spans if s["kind"] == "run")
    assert root["parent_span_id"] is None
    expected = {
        "stage": {"run"},
        "universe": {"stage"},
        "option.code": {"stage"},
        "option.smoke": {"stage"},
        "model_call": {"stage", "option.code", "option.smoke"},
        "sandbox_exec": {"step", "option.smoke", "stage"},
    }
    for span in spans:
        if span["kind"] in expected:
            assert parent_kind(span) in expected[span["kind"]], span["name"]
    in_universe = [s for s in spans if s["kind"] == "step" and parent_kind(s) == "universe"]
    assert in_universe and all(
        by_id[s["parent_span_id"]]["attributes"]["borges.universe.id"].startswith("u_")
        for s in in_universe
    )


def test_model_spans_carry_hashes_and_never_prompts(scripted_run: ScriptedRun) -> None:
    spans = read_spans(scripted_run.run_dir / "spans.jsonl")
    calls = [s for s in spans if s["kind"] == "model_call"]
    failed = [c for c in calls if c["status"] == "ERROR"]
    assert all("error.type" in c["attributes"] for c in failed)
    calls = [c for c in calls if c["status"] != "ERROR"]
    assert len(calls) >= 20
    for call in calls:
        attrs = call["attributes"]
        assert attrs["gen_ai.system"] == "nebius"
        assert attrs["gen_ai.operation.name"] == "chat"
        assert {"gen_ai.request.model", "gen_ai.response.model"} <= attrs.keys()
        assert {"gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"} <= attrs.keys()
        assert {"borges.agent.role", "borges.cache.hit", "borges.cost_usd"} <= attrs.keys()
        assert len(attrs["borges.prompt.sha256"]) == 64
        assert not any(k in attrs for k in ("gen_ai.prompt", "gen_ai.completion", "messages"))
        assert all(len(str(v)) < 200 for v in attrs.values())
    assert {c["attributes"]["borges.agent.role"] for c in calls} >= {"planner", "coder", "narrator"}


def test_both_audit_chains_verify_and_agree(scripted_run: ScriptedRun) -> None:
    run_report = verify_chain(scripted_run.run_dir / "audit.jsonl")
    global_report = verify_chain(global_audit_path(scripted_run.settings))
    assert run_report.ok and run_report.records > 50
    assert global_report.ok and global_report.records == run_report.records
