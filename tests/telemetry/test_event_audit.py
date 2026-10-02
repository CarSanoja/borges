from __future__ import annotations

from collections import Counter

from borges.telemetry.audit_verify import read_records
from tests.telemetry.conftest import ScriptedRun


def test_scripted_run_audit_covers_models_sandbox_verdicts_lifecycle(
    scripted_run: ScriptedRun,
) -> None:
    records = read_records(scripted_run.run_dir / "audit.jsonl")
    kinds = Counter(r.kind for r in records)
    assert kinds["model.call"] >= 20 and kinds["sandbox.exec"] > 0
    assert kinds["verdict.judge"] > 0 and kinds["verdict.verifier"] == 1
    lifecycle = [r.reason for r in records if r.kind == "run.lifecycle"]
    assert lifecycle == ["started", "completed"]
    assert all(r.run_id == scripted_run.run_id and r.trace_id for r in records)
    judge = next(r for r in records if r.kind == "verdict.judge")
    assert judge.decision in ("allow", "deny") and judge.principal == "agent:judge"
    model = next(r for r in records if r.kind == "model.call")
    for field in ("role", "model", "prompt_sha256", "response_sha256", "tokens_in", "cost_usd"):
        assert field in model.data
    assert {"cache_hit", "latency_s", "outcome"} <= model.data.keys()


def test_sandbox_records_link_parent_and_child_checkpoints(scripted_run: ScriptedRun) -> None:
    execs = [
        r for r in read_records(scripted_run.run_dir / "audit.jsonl") if r.kind == "sandbox.exec"
    ]
    assert all(r.data["child_checkpoint"] and r.data["parent_checkpoint"] for r in execs)
    assert all("exit_code" in r.data and "duration_s" in r.data for r in execs)
    assert any(r.data["step_id"] and r.data["option_id"] for r in execs)


def test_audit_records_link_to_spans(scripted_run: ScriptedRun) -> None:
    from borges.telemetry.trace_tree import read_spans

    ids = {s["span_id"] for s in read_spans(scripted_run.run_dir / "spans.jsonl")}
    records = read_records(scripted_run.run_dir / "audit.jsonl")
    assert all(r.span_id in ids for r in records if r.kind in ("model.call", "sandbox.exec"))
