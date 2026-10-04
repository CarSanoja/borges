from __future__ import annotations

from pathlib import Path

import pytest

from borges.llm.client import BudgetExceeded, LLMError
from borges.runs.models import RunRequest
from tests.runs.engine_fakes import Scenario, install
from tests.runs.fakes import adversary_proposal, make_rig


def types(rig, run_id: str) -> list[str]:
    return [e.type for e in rig.store.events(run_id)]


def stages(rig, run_id: str) -> list[tuple[str, str]]:
    return [
        (e.data["name"], e.data["status"]) for e in rig.store.events(run_id) if e.type == "stage"
    ]


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> Scenario:
    value = Scenario()
    install(monkeypatch, value)
    return value


async def test_max_universes_bounds_the_search(tmp_path: Path, scenario: Scenario) -> None:
    scenario.proposals = [adversary_proposal()]
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo", max_universes=2))
    assert len(snapshot.garden.universes) == 2
    assert "adversary" not in [s for s, _ in stages(rig, "r_test")]
    assert "propose" not in scenario.calls


async def test_baseline_failure_is_repaired_once(tmp_path: Path, scenario: Scenario) -> None:
    scenario.broken = {("s1", "a")}
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert scenario.calls.count("repair:s1.a:s1/a: boom") == 1
    coded = [e.data for e in rig.store.events("r_test") if e.type == "option.coded"]
    assert {
        "step_id": "s1",
        "option_id": "a",
        "ok": True,
        "attempts": 2,
        "error": None,
        "models": [],
    } in coded
    assert snapshot.plan.step("s1").option("a").code == "fixed"
    baseline = snapshot.garden.baseline
    assert baseline is not None and baseline.status == "done"


async def test_a_failed_baseline_default_is_replaced_by_its_sibling(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.broken = {("s2", "x")}
    scenario.unrepairable = True
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert snapshot.plan.step("s2").default.id == "y"
    assert any("was promoted to default" in c for c in snapshot.report.caveats)


async def test_baseline_failure_after_repair_fails_the_run(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.broken = {("s2", "x"), ("s2", "y")}
    scenario.unrepairable = True
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "failed"
    assert "baseline analysis failed" in snapshot.error
    assert types(rig, "r_test")[-2:] == ["run.failed", "run.finished"]
    assert rig.store.events("r_test")[-1].data["status"] == "failed"
    assert rig.store.meta("r_test")["status"] == "failed"
    assert rig.backend.closed


async def test_single_flip_failure_is_repaired_and_rerun(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.broken = {("s1", "b")}
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert scenario.calls.count("repair:s1.b:s1/b: boom") == 1
    universe = next(u for u in snapshot.garden.universes.values() if u.changed == ["s1"])
    assert universe.status == "done"
    assert snapshot.plan.step("s1").option("b").code == "fixed"


async def test_unrepairable_single_flip_stays_failed_without_failing_run(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.broken = {("s1", "b")}
    scenario.unrepairable = True
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    failed = [u for u in snapshot.garden.universes.values() if u.status == "failed"]
    assert ["s1"] in [u.changed for u in failed]
    assert all(u.choices["s1"] == "b" for u in failed)


async def test_budget_exceeded_fails_the_run_with_message(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.plan_error = BudgetExceeded("spend cap reached")
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "failed"
    assert snapshot.error == "BudgetExceeded: spend cap reached"
    assert rig.store.meta("r_test")["status"] == "failed"
    assert rig.backend.closed


async def test_combination_flips_only_without_a_single_flip(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.effects = {("s1", "b"): -0.6, ("s2", "y"): -0.6}
    scenario.combination_choices = [{"s1": "b", "s2": "y"}]
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert ("combination_flips", "started") in stages(rig, "r_test")
    assert scenario.combination_calls == [(2, 4)]
    assert snapshot.flip is not None and len(snapshot.flip.changes) == 2
    assert any(u.kind == "combination" for u in snapshot.garden.universes.values())


async def test_no_combination_stage_when_flip_exists_and_no_verify_without_flip(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert "combination_flips" not in [s for s, _ in stages(rig, "r_test")]

    scenario.effects = {}
    scenario.combination_choices = []
    await rig.orchestrator.execute("r_none", RunRequest(case_id="demo"))
    assert "flip.found" not in types(rig, "r_none")
    assert "verifying" not in [s for s, _ in stages(rig, "r_none")]
    snapshot = rig.orchestrator.snapshot("r_none")
    assert snapshot.report is not None and snapshot.report.minimal_flip is None


async def test_narrator_failure_keeps_the_report(tmp_path: Path, scenario: Scenario) -> None:
    scenario.narrate_error = RuntimeError("model down")
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert snapshot.report.narrative == ""
    assert snapshot.report.caveats == ["Narrative unavailable: model down"]


async def test_llm_error_on_the_adversary_leaves_a_completed_run(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.proposals = [adversary_proposal()]
    scenario.propose_error = LLMError("adversary: invalid output")
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert snapshot.report is not None
    assert not any(u.kind == "adversary" for u in snapshot.garden.universes.values())


async def test_budget_exceeded_on_the_adversary_becomes_a_caveat(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.proposals = [adversary_proposal()]
    scenario.propose_error = BudgetExceeded("spend cap reached")
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert snapshot.report is not None
    assert any("adversary" in c and "spend cap reached" in c for c in snapshot.report.caveats)
    assert ("adversary", "done") in stages(rig, "r_test")


def runtime_context(tmp_path: Path, **fields):
    from borges.runtime.checkpoints import SqliteCheckpointStore
    from borges.runtime.context import RunContext
    from borges.runtime.db import RuntimeDb

    store = SqliteCheckpointStore(RuntimeDb(tmp_path / "rt.db"))
    return RunContext("r_ctx", store, **fields), store


async def test_stage_checkpoints_are_written_for_plan_and_coding(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    context, store = runtime_context(tmp_path)
    await rig.orchestrator.execute("r_ctx", RunRequest(case_id="demo"), context=context)
    plan = store.load("r_ctx", "stage:plan")
    coded = store.load("r_ctx", "stage:coded")
    assert plan is not None and coded is not None
    assert coded["plan"]["steps"][0]["options"][0]["code"] == "code-a"
    assert coded["coding"]["options"] > 0 and "smoke_notes" in coded
    assert store.last("r_ctx")["checkpoints"] >= 2


async def test_cancel_is_honoured_at_the_next_stage_boundary(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    context, _ = runtime_context(tmp_path)
    original = scenario.entered_plan

    class Trip:
        def set(self) -> None:
            context.cancel.set("stop now")
            original.set()

    scenario.entered_plan = Trip()
    snapshot = await rig.orchestrator.execute("r_ctx", RunRequest(case_id="demo"), context=context)
    assert snapshot.status == "cancelled"
    done = [s for s in stages(rig, "r_ctx") if s[1] == "done"]
    assert ("planning", "done") in done and ("coding", "done") not in done


async def test_without_a_context_nothing_is_checkpointed(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_ctx", RunRequest(case_id="demo"))
    assert snapshot.status == "completed" and snapshot.resumed == 0


async def test_a_resumed_run_reports_every_checkpoint_it_has_persisted(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from borges.llm.client import UsageTotals
    from borges.runs.bus import EventBus
    from borges.runs.emitter import RunEmitter
    from borges.runs.pipeline import Pipeline
    from borges.runs.store import RunStore
    from borges.runtime.checkpoints import NullCheckpointStore
    from borges.runtime.context import RunContext

    store = RunStore(tmp_path)
    store.create("r_1", {})
    emitter = RunEmitter("r_1", store, EventBus(store))
    for name in ("a", "b", "c"):
        await emitter.emit("checkpoint.created", {"checkpoint_id": name})
    shell = SimpleNamespace(
        executor=SimpleNamespace(checkpoints_created=1),
        llm=SimpleNamespace(totals=UsageTotals()),
        emitter=emitter,
        context=RunContext("r_1", NullCheckpointStore(), resume_reason="restart"),
    )
    assert Pipeline._usage(shell)[1] == 3  # type: ignore[arg-type]
    shell.context = RunContext("r_1", NullCheckpointStore())
    assert Pipeline._usage(shell)[1] == 1  # type: ignore[arg-type]
