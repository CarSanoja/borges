from __future__ import annotations

from typing import Any

import pytest

from borges.analysis.models import AnalysisPlan, CodingSummary, Judgement, Option, Step
from borges.runs import plan_judging
from borges.runs.judged_ledger import JudgedLedger
from borges.runs.replan_judging import replan_admit
from tests.runs.fakes import make_plan
from tests.runs.test_plan_judging import Emitter, judged

PROXY = Option(
    id="opt_new_a",
    label="Proxy smoking",
    rationale="r",
    spec="Create proxy_smoking = ((age > 50) & (bmi > 25)).astype(int)",
    is_default=True,
)
DROP = Option(id="opt_new_b", label="Drop invalid", rationale="r", spec="Drop invalid rows")


def patch_judge(monkeypatch: pytest.MonkeyPatch, rejected: set[str]) -> list[str]:
    seen: list[str] = []

    async def judge(
        llm: Any, plan: AnalysisPlan, step: Step, option: Option, origin: str = "adversary"
    ) -> Judgement:
        seen.append(f"{origin}:{step.id}.{option.id}")
        ok = option.id not in rejected
        return Judgement(defensibility=0.8 if ok else 0.1, accepted=ok, reason="invented")

    monkeypatch.setattr(plan_judging, "judge_option", judge)
    return seen


class Holding:
    def __init__(self, keys: set[str]) -> None:
        self.keys = keys

    def holds(self, key: str) -> bool:
        return key in self.keys


async def test_a_replanned_option_the_judge_rejects_is_not_coded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = patch_judge(monkeypatch, {"opt_new_a"})
    plan, emitter, summary = make_plan(), Emitter(), CodingSummary()
    admit = replan_admit(None, plan, emitter, summary, JudgedLedger(), None, None)
    kept = await admit(plan.steps[0], [PROXY, DROP])
    assert [o.id for o in kept] == ["opt_new_b"]
    assert seen == ["planner:s1.opt_new_a", "planner:s1.opt_new_b"]
    assert judged(emitter)["opt_new_a"]["accepted"] is False
    assert summary.options_dropped_by_judge == 1


async def test_model_armor_screens_the_replan_before_the_judge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = patch_judge(monkeypatch, set())

    async def screen(step_id: str, options: list[Option]) -> list[Option]:
        return [o for o in options if o.id != "opt_new_b"]

    plan = make_plan()
    admit = replan_admit(None, plan, Emitter(), CodingSummary(), JudgedLedger(), None, screen)
    assert [o.id for o in await admit(plan.steps[0], [PROXY, DROP])] == ["opt_new_a"]
    assert seen == ["planner:s1.opt_new_a"]


async def test_a_scripted_run_keeps_a_replan_its_fixtures_hold_no_verdict_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = patch_judge(monkeypatch, {"opt_new_a", "opt_new_b"})
    llm = Holding({"judge:planner:s1.opt_new_b"})
    plan = make_plan()
    admit = replan_admit(llm, plan, Emitter(), CodingSummary(), JudgedLedger(), None, None)
    assert [o.id for o in await admit(plan.steps[0], [PROXY, DROP])] == ["opt_new_a"]
    assert seen == ["planner:s1.opt_new_b"]
