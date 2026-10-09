from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Proposal, Step
from borges.runs import coded_refill
from borges.runs.coded_refill import LOST, refill_coded
from tests.analysis.test_plan_refill import wide_plan
from tests.runs.fakes import make_option
from tests.runs.test_plan_judging import Emitter


def pipeline(screened: set[str] = frozenset()) -> SimpleNamespace:
    async def planner_options(step_id: str, options: list[Option]) -> list[Option]:
        return [o for o in options if o.id not in screened]

    return SimpleNamespace(
        llm=None,
        emitter=Emitter(),
        armor_stage=SimpleNamespace(planner_options=planner_options),
        smoke=None,
        memory=None,
        coding=CodingSummary(),
    )


def patch(monkeypatch: pytest.MonkeyPatch, fresh: dict[str, list[str]], passing: set[str]) -> Any:
    calls: dict[str, Any] = {"refill": [], "coded": []}

    async def refill(llm, plan: AnalysisPlan, step: Step, lost, failed: bool = False):
        calls["refill"].append((step.id, [(o.id, reason) for o, reason in lost], failed))
        return [make_option(i) for i in fresh.get(step.id, [])]

    async def judge_and_code(llm, plan, emitter, proposal: Proposal, smoke, memory, origin):
        calls["coded"].append((proposal.option.id, origin))
        return (proposal.step_id, proposal.option) if proposal.option.id in passing else None

    monkeypatch.setattr(coded_refill, "propose_refill", refill)
    monkeypatch.setattr(coded_refill, "judge_and_code", judge_and_code)
    return calls


def coded(planned: AnalysisPlan, kept: dict[str, int]) -> AnalysisPlan:
    plan = planned.model_copy(deep=True)
    for step in plan.steps:
        step.options = step.options[: kept.get(step.id, len(step.options))]
    return plan


async def test_steps_the_coder_collapsed_get_new_alternatives_judged_and_coded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = patch(monkeypatch, {"b": ["b_new"], "c": ["c_new", "c_bad"], "m": ["m_new"]}, {"b_new"})
    planned = wide_plan({"a": 2, "b": 2, "c": 3, "m": 2})
    plan = coded(planned, {"b": 1, "c": 1, "m": 1})
    runner = pipeline(screened={"c_bad"})
    await refill_coded(runner, planned, plan)
    assert sorted(calls["refill"]) == [
        ("b", [("b1", LOST)], True),
        ("c", [("c1", LOST), ("c2", LOST)], True),
        ("m", [("m1", LOST)], True),
    ]
    assert sorted(calls["coded"]) == [
        ("b_new", "planner"),
        ("c_new", "planner"),
        ("m_new", "planner"),
    ]
    assert [o.id for o in plan.step("b").options] == ["b0", "b_new"]
    assert [o.id for o in plan.step("c").options] == ["c0"]
    assert runner.coding.options_added_after_judge == 1
    assert runner.emitter.events[-1][0] == "plan.ready"


async def test_nothing_is_refilled_while_enough_steps_still_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = patch(monkeypatch, {"c": ["c_new"]}, {"c_new"})
    planned = wide_plan({"a": 2, "b": 2, "c": 2, "m": 2})
    plan = coded(planned, {"c": 1})
    runner = pipeline()
    await refill_coded(runner, planned, plan)
    assert calls["refill"] == [] and runner.emitter.events == []
    assert [o.id for o in plan.step("c").options] == ["c0"]
