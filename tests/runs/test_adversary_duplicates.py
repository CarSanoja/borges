from __future__ import annotations

from typing import Any

import pytest

from borges.analysis.models import Judgement
from borges.runs import adversary_round
from borges.runs.adversary_duplicates import drop_duplicates
from borges.runs.adversary_round import run_adversary_round
from borges.runs.judged_ledger import JudgedLedger
from tests.runs.fakes import adversary_proposal, make_option, make_plan
from tests.runs.test_adversary_round import Emitter, Runner, patch


def planner_option(option_id: str) -> Any:
    return make_option(option_id).model_copy(update={"label": "psychological well-being mean"})


def ledger_with(accepted: bool) -> JudgedLedger:
    ledger = JudgedLedger()
    judgement = Judgement(
        defensibility=0.7 if accepted else 0.5, accepted=accepted, reason="because", source=None
    )
    ledger.record("s2", planner_option("alt_wellbeing"), judgement)
    return ledger


def duplicate() -> Any:
    proposal = adversary_proposal(option_id="adv_wellbeing")
    proposal.option = proposal.option.model_copy(update={"label": "Psychological well-being mean"})
    return proposal


async def test_duplicate_of_rejected_planner_alternative_reuses_the_judgement() -> None:
    emitter = Emitter()
    fresh = await drop_duplicates(make_plan(), emitter, ledger_with(False), [duplicate()])
    assert fresh == []
    [(kind, data)] = emitter.events
    assert kind == "option.judged" and data["accepted"] is False
    assert data["origin"] == "adversary" and data["defensibility"] == 0.5
    assert "alt_wellbeing" in data["reason"] and "because" in data["reason"]


async def test_duplicate_of_accepted_planner_alternative_is_skipped_silently() -> None:
    emitter = Emitter()
    fresh = await drop_duplicates(make_plan(), emitter, ledger_with(True), [duplicate()])
    assert fresh == [] and emitter.events == []


async def test_duplicate_of_an_option_in_the_plan_is_skipped() -> None:
    plan = make_plan()
    proposal = adversary_proposal(option_id="adv_y")
    assert await drop_duplicates(plan, Emitter(), None, [proposal]) == []


async def test_new_proposal_passes() -> None:
    fresh = await drop_duplicates(
        make_plan(), Emitter(), ledger_with(False), [adversary_proposal()]
    )
    assert len(fresh) == 1


@pytest.mark.parametrize("accepted", [False, True])
async def test_round_neither_judges_nor_runs_the_duplicate(
    monkeypatch: pytest.MonkeyPatch, accepted: bool
) -> None:
    judged: list[str] = []

    async def propose(*args: Any) -> Any:
        return [duplicate()]

    async def judge(llm: Any, plan: Any, step: Any, option: Any) -> Judgement:
        judged.append(option.id)
        return Judgement(defensibility=0.9, accepted=True, reason="ok")

    patch(monkeypatch, propose, judge)
    runner = Runner()
    emitter = Emitter()
    out = await run_adversary_round(
        None, make_plan(), runner, emitter, None, None, ledger_with(accepted)
    )
    assert out == [] and judged == [] and runner.ran == []
    assert not [e for e in emitter.events if e[0] == "option.proposed"]
    assert adversary_round.judge_option is not None
