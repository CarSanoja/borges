from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from borges.analysis.models import AnalysisPlan, CodingSummary, Judgement, Option, Step
from borges.garden.search import changes_for
from borges.llm.client import BudgetExceeded, LLMError
from borges.runs import plan_judging
from borges.runs.models import RunRequest
from borges.runs.plan_judging import judge_plan_options
from tests.runs.engine_fakes import install
from tests.runs.engine_scenario import Scenario
from tests.runs.fakes import make_plan, make_rig


class Emitter:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append((event_type, data))


def patch_judge(
    monkeypatch: pytest.MonkeyPatch, rejected: set[str], failing: set[str]
) -> list[str]:
    seen: list[str] = []

    async def judge(
        llm: Any, plan: AnalysisPlan, step: Step, option: Option, origin: str = "adversary"
    ) -> Judgement:
        seen.append(f"{origin}:{step.id}.{option.id}")
        if option.id in failing:
            raise LLMError(f"judge:planner:{step.id}.{option.id}: invalid output")
        ok = option.id not in rejected
        return Judgement(defensibility=0.8 if ok else 0.1, accepted=ok, reason="r", source="S")

    monkeypatch.setattr(plan_judging, "judge_option", judge)
    return seen


def judged(emitter: Emitter) -> dict[str, dict[str, Any]]:
    return {d["option_id"]: d for t, d in emitter.events if t == "option.judged"}


async def test_defaults_are_never_judged(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = patch_judge(monkeypatch, set(), set())
    await judge_plan_options(None, make_plan(), Emitter(), CodingSummary())
    assert sorted(seen) == ["planner:s1.b", "planner:s2.y"]


async def test_rejected_alternative_is_dropped_and_flagged_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_judge(monkeypatch, {"b"}, set())
    plan, emitter, summary = make_plan(), Emitter(), CodingSummary()
    await judge_plan_options(None, plan, emitter, summary)
    assert [o.id for o in plan.step("s1").options] == ["a"]
    assert [o.id for o in plan.step("s2").options] == ["x", "y"]
    events = judged(emitter)
    assert events["b"]["accepted"] is False and events["b"]["origin"] == "planner"
    assert events["y"]["accepted"] is True and events["y"]["origin"] == "planner"
    assert summary.options_dropped_by_judge == 1


async def test_accepted_alternative_carries_its_defensibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_judge(monkeypatch, set(), set())
    plan = make_plan()
    await judge_plan_options(None, plan, Emitter(), CodingSummary())
    assert plan.step("s2").option("y").defensibility == 0.8
    changes = changes_for(plan, {"s1": "a", "s2": "y"})
    assert [c.defensibility for c in changes] == [0.8]


async def test_judge_exception_drops_the_alternative(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_judge(monkeypatch, set(), {"y"})
    plan, emitter, summary = make_plan(), Emitter(), CodingSummary()
    await judge_plan_options(None, plan, emitter, summary)
    event = judged(emitter)["y"]
    assert event["accepted"] is False and "judge failed" in event["reason"]
    assert event["origin"] == "planner"
    assert [o.id for o in plan.step("s2").options] == ["x"]
    assert summary.options_dropped_by_judge == 1


async def test_budget_exceeded_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    async def judge(*args: Any, **kwargs: Any) -> Judgement:
        raise BudgetExceeded("cap")

    monkeypatch.setattr(plan_judging, "judge_option", judge)
    with pytest.raises(BudgetExceeded):
        await judge_plan_options(None, make_plan(), Emitter(), CodingSummary())


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> Scenario:
    value = Scenario()
    install(monkeypatch, value)
    return value


async def test_rejected_alternative_is_never_coded_or_run(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.planner_rejects = {"b"}
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    events = rig.store.events("r_test")
    judged_events = [e.data for e in events if e.type == "option.judged"]
    rejected = next(d for d in judged_events if d["option_id"] == "b")
    assert rejected["accepted"] is False and rejected["origin"] == "planner"
    coded = {e.data["option_id"] for e in events if e.type == "option.coded"}
    assert "b" not in coded and "y" in coded
    ran = [choices for executor in scenario.executors for choices, _ in executor.runs]
    assert ran and all(choices.get("s1") != "b" for choices in ran)
    assert all(u.choices.get("s1") != "b" for u in snapshot.garden.universes.values())
    assert snapshot.report.coding.options_dropped_by_judge == 1


async def test_accepted_alternative_runs_and_defaults_are_not_judged(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert sorted(scenario.planner_judged) == ["s1.b", "s2.y"]
    assert any(u.choices.get("s1") == "b" for u in snapshot.garden.universes.values())
    assert snapshot.report.coding.options_dropped_by_judge == 0
