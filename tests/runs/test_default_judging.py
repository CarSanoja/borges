from __future__ import annotations

from typing import Any

import pytest

from borges.analysis.models import AnalysisPlan, CodingSummary, Judgement, Option, Step
from borges.runs import default_judging, plan_judging
from borges.runs.plan_judging import judge_plan_options
from tests.runs.fakes import make_option, make_plan
from tests.runs.test_plan_judging import Emitter, judged


def patch_judge(
    monkeypatch: pytest.MonkeyPatch, scores: dict[str, float], failing: frozenset[str] = frozenset()
) -> None:
    async def judge(
        llm: Any, plan: AnalysisPlan, step: Step, option: Option, origin: str = "adversary"
    ) -> Judgement:
        if option.id in failing:
            raise RuntimeError("timeout")
        score = scores.get(option.id, 0.8)
        return Judgement(defensibility=score, accepted=score >= 0.6, reason=f"{option.id} why")

    monkeypatch.setattr(plan_judging, "judge_option", judge)


def patch_refill(monkeypatch: pytest.MonkeyPatch, proposed: list[Option]) -> list[Any]:
    calls: list[Any] = []

    async def refill(llm: Any, plan: AnalysisPlan, step: Step, rejected: Any) -> list[Option]:
        calls.append((step.id, [o.id for o, _ in rejected]))
        return proposed

    monkeypatch.setattr(default_judging, "propose_refill", refill)
    return calls


async def test_rejected_default_is_replaced_by_the_best_accepted_alternative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = make_plan()
    plan.step("s2").options.append(make_option("z"))
    patch_judge(monkeypatch, {"x": 0.1, "y": 0.7, "z": 0.9})
    summary = CodingSummary()
    await judge_plan_options(None, plan, Emitter(), summary)
    step = plan.step("s2")
    assert step.default.id == "z"
    assert [o.id for o in step.options] == ["y", "z"]
    assert sum(o.is_default for o in step.options) == 1
    assert summary.defaults_replaced == ["s2: label x -> label z: x why"]
    assert summary.options_dropped_by_judge == 0


async def test_rejected_default_without_alternatives_asks_the_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = make_plan()
    patch_judge(monkeypatch, {"a": 0.2, "b": 0.1, "c": 0.8})
    calls = patch_refill(monkeypatch, [make_option("c")])
    summary = CodingSummary()
    await judge_plan_options(None, plan, Emitter(), summary)
    assert ("s1", ["a"]) in calls
    assert plan.step("s1").default.id == "c"
    assert [o.id for o in plan.step("s1").options] == ["c"]
    assert summary.defaults_replaced == ["s1: label a -> label c: a why"]


async def test_default_without_any_accepted_replacement_is_kept_and_disputed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = make_plan()
    patch_judge(monkeypatch, {"a": 0.2, "b": 0.1, "c": 0.3})
    patch_refill(monkeypatch, [make_option("c")])
    summary = CodingSummary()
    await judge_plan_options(None, plan, Emitter(), summary)
    assert plan.step("s1").default.id == "a"
    assert summary.defaults_replaced == []
    assert summary.defaults_disputed == ["s1: label a: a why"]


async def test_the_users_own_analysis_is_kept_with_the_judges_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = make_plan()
    patch_judge(monkeypatch, {"a": 0.2})
    calls = patch_refill(monkeypatch, [make_option("c")])
    summary = CodingSummary()
    await judge_plan_options(None, plan, Emitter(), summary, keep_defaults=True)
    assert plan.step("s1").default.id == "a" and calls == []
    assert summary.defaults_replaced == [] and summary.defaults_disputed == []
    assert summary.defaults_kept == ["s1: label a: a why"]


async def test_a_judge_failure_never_replaces_a_default(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = make_plan()
    patch_judge(monkeypatch, {}, frozenset({"x"}))
    summary, emitter = CodingSummary(), Emitter()
    await judge_plan_options(None, plan, emitter, summary)
    assert plan.step("s2").default.id == "x"
    assert "x" not in judged(emitter)
    assert summary.defaults_replaced == [] and summary.defaults_disputed == []
