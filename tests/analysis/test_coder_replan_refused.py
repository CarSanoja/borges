from __future__ import annotations

from pathlib import Path

import pytest

from borges.analysis import coder_checks
from borges.analysis.coder import code_plan
from borges.analysis.models import Judgement, Option
from borges.llm.client import LLMError
from borges.runs.judged_ledger import JudgedLedger
from tests.analysis.fakes import FakeLLM, make_plan
from tests.analysis.test_coder_replan import GOOD, REPLAN, Log, code, config, planned, scripted


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", lambda code, kind, intent="": [])


def ledger_rejecting(option_id: str) -> JudgedLedger:
    ledger = JudgedLedger()
    rejected = Option(id=option_id, label=f"L {option_id}", rationale="r", spec="other words")
    ledger.record("m1", rejected, Judgement(defensibility=0.4, accepted=False, reason="estimand"))
    return ledger


async def test_the_replan_drops_an_option_the_judge_rejected(tmp_path: Path) -> None:
    llm = FakeLLM(
        scripted(
            **{
                REPLAN: {"options": [planned("binary", True), planned("robust")]},
                "coder:m1.binary": code(GOOD),
                "coder:m1.robust": code(GOOD),
            }
        )
    )
    log = Log()
    smoke = config(tmp_path, log)
    smoke.refused = ledger_rejecting("binary").refused
    coded = await code_plan(llm, make_plan(), log.on_coded, smoke=smoke)
    step = coded.step("m1")
    assert [o.id for o in step.options] == ["robust"] and step.options[0].is_default
    assert all(c.key != "coder:m1.binary" for c in llm.calls)
    assert log.replans == [("m1", ["ols", "welch"], ["robust"])]


async def test_a_replan_of_only_rejected_options_fails_as_without_a_replan(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{REPLAN: {"options": [planned("binary", True)]}}))
    smoke = config(tmp_path, Log())
    smoke.refused = ledger_rejecting("binary").refused
    with pytest.raises(LLMError, match="no option passed its smoke run"):
        await code_plan(llm, make_plan(), smoke=smoke)


def test_an_accepted_or_unknown_option_is_not_refused() -> None:
    ledger = ledger_rejecting("binary")
    kept = Option(id="nb", label="Negative binomial", rationale="r", spec="nb")
    ledger.record("m1", kept, Judgement(defensibility=0.8, accepted=True, reason="ok"))
    assert ledger.refused("m1", Option(id="binary", label="L binary", rationale="r", spec="x"))
    assert not ledger.refused("m1", kept)
    assert not ledger.refused("d1", Option(id="binary", label="L binary", rationale="r", spec="x"))
