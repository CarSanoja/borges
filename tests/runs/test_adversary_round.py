from __future__ import annotations

from typing import Any

import pytest

from borges.analysis.models import Judgement
from borges.llm.client import BudgetExceeded, LLMError
from borges.runs import adversary_round
from borges.runs.adversary_round import run_adversary_round
from tests.runs.fakes import adversary_proposal, make_plan


class Emitter:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append((event_type, data))


class Runner:
    def __init__(self) -> None:
        self.ran: list[Any] = []

    async def run_many(self, choices: list[dict[str, str]], kind: str) -> list[Any]:
        self.ran.extend(choices)
        return []


def patch(monkeypatch: pytest.MonkeyPatch, propose: Any, judge: Any) -> None:
    monkeypatch.setattr(adversary_round, "propose_options", propose)
    monkeypatch.setattr(adversary_round, "judge_option", judge)

    async def code_option(llm: Any, plan: Any, step: Any, option: Any) -> str:
        return "code"

    monkeypatch.setattr(adversary_round, "code_option", code_option)

    async def review_proposal(llm: Any, plan: Any, emitter: Any, step: Any, option: Any) -> Any:
        return option

    monkeypatch.setattr(adversary_round, "review_proposal", review_proposal)


async def test_propose_llm_error_returns_no_universes(monkeypatch: pytest.MonkeyPatch) -> None:
    async def propose(*args: Any) -> Any:
        raise LLMError("adversary: invalid output")

    async def judge(*args: Any) -> Any:
        raise AssertionError("not reached")

    patch(monkeypatch, propose, judge)
    runner = Runner()
    assert await run_adversary_round(None, make_plan(), runner, Emitter(), None) == []
    assert runner.ran == []


async def test_judge_llm_error_rejects_only_that_proposal(monkeypatch: pytest.MonkeyPatch) -> None:
    async def propose(*args: Any) -> Any:
        return [adversary_proposal(option_id="bad"), adversary_proposal(option_id="good")]

    async def judge(llm: Any, plan: Any, step: Any, option: Any) -> Judgement:
        if option.id == "bad":
            raise LLMError("judge:s2.bad: invalid output")
        return Judgement(defensibility=0.8, accepted=True, reason="ok", source="http://s")

    patch(monkeypatch, propose, judge)
    emitter = Emitter()
    runner = Runner()
    await run_adversary_round(None, make_plan(), runner, emitter, None)
    judged = {d["option_id"]: d for t, d in emitter.events if t == "option.judged"}
    assert judged["bad"]["accepted"] is False and "judge failed" in judged["bad"]["reason"]
    assert judged["good"]["accepted"] is True
    assert len(runner.ran) == 1


async def test_budget_exceeded_is_still_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    async def propose(*args: Any) -> Any:
        return [adversary_proposal()]

    async def judge(*args: Any) -> Any:
        raise BudgetExceeded("cap")

    patch(monkeypatch, propose, judge)
    with pytest.raises(BudgetExceeded):
        await run_adversary_round(None, make_plan(), Runner(), Emitter(), None)
