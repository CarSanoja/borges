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
    assert {"step_id": "s1", "option_id": "a", "ok": True, "attempts": 2, "error": None} in coded
    assert snapshot.plan.step("s1").option("a").code == "fixed"
    baseline = snapshot.garden.baseline
    assert baseline is not None and baseline.status == "done"


async def test_baseline_failure_after_repair_fails_the_run(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.broken = {("s2", "x")}
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
    assert [u.changed for u in failed] == [["s1"]]


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
    assert scenario.combination_calls == [(2, 7)]
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


async def test_judge_failure_on_one_key_rejects_only_that_option(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.proposals = [adversary_proposal()]
    scenario.judge_errors = {scenario.proposals[0].option.id}
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed" and snapshot.report is not None
    judged = [e.data for e in rig.store.events("r_test") if e.type == "option.judged"]
    assert judged and judged[0]["accepted"] is False and "judge" in judged[0]["reason"]


async def test_budget_exceeded_on_the_narrator_keeps_report_with_caveat(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.narrate_error = BudgetExceeded("spend cap reached")
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert snapshot.report is not None
    assert any("Narrative unavailable" in c for c in snapshot.report.caveats)


async def test_raising_verification_keeps_the_flip_unverified(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.verify_error = RuntimeError("sandbox down")
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert snapshot.report is not None and snapshot.report.minimal_flip is not None
    assert snapshot.report.minimal_flip.reproduced is None
    assert any("unverified" in c for c in snapshot.report.caveats)


async def test_non_reproduced_flip_adds_a_caveat(tmp_path: Path, scenario: Scenario) -> None:
    scenario.reproduced = False
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.report is not None
    assert snapshot.report.minimal_flip.reproduced is False
    assert any("did not reproduce" in c for c in snapshot.report.caveats)


async def test_pipeline_caveats_survive_narrator_caveats(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.reproduced = False
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.report is not None
    assert "caveat" in snapshot.report.caveats
    assert any("did not reproduce" in c for c in snapshot.report.caveats)


async def test_failed_universes_add_a_caveat(tmp_path: Path, scenario: Scenario) -> None:
    scenario.broken = {("s1", "b")}
    scenario.unrepairable = True
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.report is not None
    assert any("could not run" in c for c in snapshot.report.caveats)


async def test_exhausted_universe_budget_adds_caveats(tmp_path: Path, scenario: Scenario) -> None:
    scenario.proposals = [adversary_proposal()]
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo", max_universes=2))
    assert snapshot.report is not None
    joined = " ".join(snapshot.report.caveats)
    assert "single-decision" in joined and "adversary stage" in joined


async def test_step_timeout_setting_reaches_the_executor(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert scenario.executors[0].kwargs["step_timeout_s"] == 120.0
