from __future__ import annotations

from typing import Any

import pytest

from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.runs import plan_judging
from borges.runs.plan_judging import judge_plan_options
from tests.analysis.test_plan_refill import wide_plan
from tests.runs.fakes import make_option
from tests.runs.test_plan_judging import Emitter, judged, patch_judge


def patch_refill(monkeypatch: pytest.MonkeyPatch, fresh: dict[str, list[str]]) -> list[Any]:
    calls: list[Any] = []

    async def refill(llm: Any, plan: AnalysisPlan, step: Step, rejected: Any) -> list[Option]:
        calls.append((step.id, [(o.id, reason) for o, reason in rejected]))
        return [make_option(i) for i in fresh.get(step.id, [])]

    monkeypatch.setattr(plan_judging, "propose_refill", refill)
    return calls


async def test_a_plan_the_judge_collapses_gets_new_alternatives_judged_in_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_judge(monkeypatch, {"a1", "c1", "m1", "c_new"}, set())
    calls = patch_refill(monkeypatch, {"a": ["a_new"], "c": ["c_new"], "m": ["m_new"]})
    plan = wide_plan({"a": 2, "b": 2, "c": 2, "m": 2})
    emitter, summary = Emitter(), CodingSummary()
    await judge_plan_options(None, plan, emitter, summary)
    assert sorted(calls) == [("a", [("a1", "r")]), ("c", [("c1", "r")]), ("m", [("m1", "r")])]
    assert [o.id for o in plan.step("a").options] == ["a0", "a_new"]
    assert [o.id for o in plan.step("c").options] == ["c0"]
    assert [o.id for o in plan.step("m").options] == ["m0", "m_new"]
    assert plan.step("a").option("a_new").defensibility == 0.8
    assert judged(emitter)["c_new"]["accepted"] is False
    assert summary.options_dropped_by_judge == 4 and summary.options_added_after_judge == 2
    assert emitter.events[-1][0] == "plan.ready"


async def test_new_alternatives_flagged_by_the_screen_are_never_judged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = patch_judge(monkeypatch, {"a1", "c1", "m1"}, set())
    patch_refill(monkeypatch, {"a": ["a_new", "a_bad"]})
    plan = wide_plan({"a": 2, "b": 2, "c": 2, "m": 2})

    async def screen(step_id: str, options: list[Option]) -> list[Option]:
        return [o for o in options if o.id != "a_bad"]

    await judge_plan_options(None, plan, Emitter(), CodingSummary(), screen=screen)
    assert "planner:a.a_bad" not in seen
    assert [o.id for o in plan.step("a").options] == ["a0", "a_new"]


async def test_no_refill_while_enough_steps_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_judge(monkeypatch, {"a1"}, set())
    calls = patch_refill(monkeypatch, {"a": ["a_new"]})
    plan = wide_plan({"a": 2, "b": 2, "c": 2, "m": 2})
    await judge_plan_options(None, plan, Emitter(), CodingSummary())
    assert calls == [] and [o.id for o in plan.step("a").options] == ["a0"]
