from __future__ import annotations

from pathlib import Path

import pytest

from borges.llm.client import BudgetExceeded
from borges.runs.models import RunRequest
from tests.runs.engine_fakes import install
from tests.runs.engine_scenario import Scenario
from tests.runs.fakes import adversary_proposal, make_rig


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> Scenario:
    value = Scenario()
    install(monkeypatch, value)
    return value


async def test_judge_failure_on_one_key_rejects_only_that_option(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.proposals = [adversary_proposal()]
    scenario.judge_errors = {scenario.proposals[0].option.id}
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed" and snapshot.report is not None
    judged = [
        e.data
        for e in rig.store.events("r_test")
        if e.type == "option.judged" and e.data["origin"] == "adversary"
    ]
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


async def test_every_caveat_is_computed_and_the_narrator_writes_the_summary_only(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.reproduced = False
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.report is not None
    assert snapshot.report.narrative == "story"
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


async def test_budget_exceeded_during_single_flip_repair_keeps_the_report(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.broken = {("s1", "b")}
    scenario.repair_error = BudgetExceeded("run cap")
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert snapshot.report is not None
    assert snapshot.garden.baseline is not None
    assert len(snapshot.garden.universes) > 1
    assert any("single-decision flips stopped early" in c for c in snapshot.report.caveats)


async def test_budget_exceeded_during_combinations_keeps_the_report(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.effects = {}
    scenario.broken = {("s2", "y")}
    scenario.repair_error = BudgetExceeded("run cap")
    scenario.combination_choices = [{"s1": "b", "s2": "x"}]
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "completed"
    assert snapshot.report is not None


async def test_budget_exceeded_on_the_baseline_repair_still_fails_the_run(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.broken = {("s1", "a")}
    scenario.repair_error = BudgetExceeded("run cap")
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert snapshot.status == "failed"
    assert snapshot.report is None
