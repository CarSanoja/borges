from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from borges.analysis.models import DecisionRule
from borges.runs.models import RunRequest
from tests.runs.engine_fakes import Scenario, install
from tests.runs.fakes import adversary_proposal, make_rig, parquet_bytes


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


async def test_full_run_emits_ordered_events(tmp_path: Path, scenario: Scenario) -> None:
    scenario.proposals = [adversary_proposal()]
    rig = make_rig(tmp_path)
    run_id = "r_test"
    snapshot = await rig.orchestrator.execute(run_id, RunRequest(case_id="demo"))

    events = rig.store.events(run_id)
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert events[0].type == "run.started"
    assert events[0].data["case_id"] == "demo"
    assert events[0].data["mode"] == "live"
    assert events[0].data["max_universes"] == 10
    assert events[-1].type == "run.finished" and events[-1].data["status"] == "completed"
    assert stages(rig, run_id) == [
        (name, status)
        for name in (
            "profiling",
            "planning",
            "coding",
            "baseline",
            "single_flips",
            "adversary",
            "verifying",
            "narrating",
        )
        for status in ("started", "done")
    ]
    order = types(rig, run_id)
    assert order.index("flip.found") < order.index("flip.verified") < order.index("report.ready")
    assert order.count("plan.ready") == 3
    assert order.count("option.proposed") == 1 and order.count("option.judged") == 1
    assert "usage" in order
    assert snapshot.status == "completed"
    assert snapshot.report is not None and snapshot.report.narrative == "story"
    assert snapshot.flip is not None and snapshot.flip.reproduced is True
    assert snapshot.flip.changes[0].step_id == "s2"
    assert len(snapshot.garden.universes) == 4
    kinds = sorted(u.kind for u in snapshot.garden.universes.values())
    assert kinds == ["adversary", "baseline", "single", "single"]
    assert rig.backend.closed


async def test_adversary_option_enters_plan_with_code_and_defensibility(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.proposals = [adversary_proposal()]
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    option = snapshot.plan.step("s2").option("adv")
    assert option.code == "code-adv"
    assert option.defensibility == 0.8
    assert option.source == "http://s"
    assert option.origin == "adversary"


async def test_rejected_adversary_option_is_not_run(tmp_path: Path, scenario: Scenario) -> None:
    scenario.proposals = [adversary_proposal()]
    scenario.accept = False
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert not any(u.kind == "adversary" for u in snapshot.garden.universes.values())
    assert [o.id for o in snapshot.plan.step("s2").options] == ["x", "y"]


async def test_run_options_override_factories_and_pass_fixtures(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    await rig.orchestrator.execute(
        "r_test", RunRequest(case_id="demo", llm="scripted", max_universes=3)
    )
    call = rig.factory_calls[0]
    assert call["mode"] == "scripted"
    assert call["fixtures_dir"] == tmp_path / "cases" / "demo" / "fixtures"
    started = rig.store.events("r_test")[0]
    assert started.data["llm"] == "scripted" and started.data["max_universes"] == 3


async def test_meta_is_updated_at_the_end(tmp_path: Path, scenario: Scenario) -> None:
    rig = make_rig(tmp_path)
    await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    meta = rig.store.meta("r_test")
    assert meta["status"] == "completed"
    assert meta["verdict"] == "SHIP"
    assert meta["flipped_verdict"] == "DON'T SHIP"
    assert meta["cost_usd"] == 0.01
    assert meta["n_universes"] == 3


async def test_start_returns_id_and_streams_to_subscribers(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    run_id = await rig.orchestrator.start(RunRequest(case_id="demo"))
    assert run_id.startswith("r_") and len(run_id.split("_")) == 3
    assert rig.store.exists(run_id)
    received = [event.type async for event in rig.bus.subscribe(run_id)]
    assert received[0] == "run.started" and received[-1] in {"run.finished", "run.failed"}
    snapshot = await rig.orchestrator.wait(run_id)
    assert snapshot.status == "completed"
    await asyncio.sleep(0)
    assert rig.orchestrator.tasks == {}
    assert rig.store.list_runs()[0].run_id == run_id


async def test_start_with_upload_requires_question_and_rule(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    with pytest.raises(ValueError, match="question and a decision rule"):
        await rig.orchestrator.start(RunRequest(), data=parquet_bytes())
    with pytest.raises(ValueError, match="case_id"):
        await rig.orchestrator.start(RunRequest())
    with pytest.raises(KeyError):
        await rig.orchestrator.start(RunRequest(case_id="missing"))
    assert rig.store.list_runs() == []


async def test_upload_run_has_no_case_and_no_fixtures(tmp_path: Path, scenario: Scenario) -> None:
    rig = make_rig(tmp_path)
    request = RunRequest(question="q?", decision_rule=DecisionRule(metric="m"))
    run_id = await rig.orchestrator.start(request, data=parquet_bytes(), dataset_name="mine.csv")
    snapshot = await rig.orchestrator.wait(run_id)
    assert snapshot.case_id is None and snapshot.question == "q?"
    assert rig.factory_calls[0]["fixtures_dir"] is None
    assert snapshot.status == "completed"


async def test_unreadable_upload_fails_the_run(tmp_path: Path, scenario: Scenario) -> None:
    rig = make_rig(tmp_path)
    request = RunRequest(question="q?", decision_rule=DecisionRule(metric="m"))
    run_id = await rig.orchestrator.start(request, data=b"not parquet")
    snapshot = await rig.orchestrator.wait(run_id)
    assert snapshot.status == "failed"
    assert "not a readable parquet" in snapshot.error


async def test_cancelled_run_is_recorded_as_failed(tmp_path: Path, scenario: Scenario) -> None:
    rig = make_rig(tmp_path)
    scenario.hang = True
    run_id = await rig.orchestrator.start(RunRequest(case_id="demo"))
    await scenario.entered_plan.wait()
    await rig.orchestrator.shutdown()
    snapshot = rig.orchestrator.snapshot(run_id)
    assert snapshot.status == "failed"
    assert snapshot.error == "run cancelled"
    assert rig.store.meta(run_id)["status"] == "failed"


async def test_universe_detail_for_the_flip_and_for_a_plain_universe(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    flip_id = snapshot.flip.universe_id
    detail = rig.orchestrator.universe_detail("r_test", flip_id)
    assert detail.reproduce_command == "python go.py"
    assert [s.changed for s in detail.steps] == [False, True]
    assert detail.steps[1].option.code == "code-y"
    assert detail.steps[0].trace.rows_before == 3
    assert detail.steps[1].checkpoint_id == "cp_s2_y"

    baseline = snapshot.garden.baseline
    plain = rig.orchestrator.universe_detail("r_test", baseline.id)
    assert plain.reproduce_command == "python steps/s1__a.py && python steps/s2__x.py"
    with pytest.raises(KeyError):
        rig.orchestrator.universe_detail("r_test", "u_missing")


async def test_record_dir_is_forwarded_to_the_llm_factory(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    rig.orchestrator.record_dir = tmp_path / "rec"
    await rig.orchestrator.execute("r_rec", RunRequest(case_id="demo"))
    assert rig.factory_calls[0]["record_dir"] == tmp_path / "rec"


async def test_active_and_live_counts_come_from_running_tasks(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    scenario.hang = True
    assert (rig.orchestrator.active_count(), rig.orchestrator.live_count()) == (0, 0)
    await rig.orchestrator.start(RunRequest(case_id="demo", llm="scripted"))
    await rig.orchestrator.start(RunRequest(case_id="demo", llm="nebius"))
    assert (rig.orchestrator.active_count(), rig.orchestrator.live_count()) == (2, 1)
    await rig.orchestrator.shutdown()
    await asyncio.sleep(0)
    assert (rig.orchestrator.active_count(), rig.orchestrator.live_count()) == (0, 0)


async def test_failed_append_in_finish_still_drops_the_bus_channel(
    tmp_path: Path, scenario: Scenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = make_rig(tmp_path)
    real_append = rig.store.append

    def append(event) -> None:
        if event.type == "run.finished":
            raise OSError("no space left on device")
        real_append(event)

    monkeypatch.setattr(rig.store, "append", append)
    with pytest.raises(OSError):
        await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert not rig.bus.is_live("r_test")
    assert rig.store.meta("r_test")["status"] == "completed"
