from __future__ import annotations

from borges.analysis.models import CodingSummary, Judgement
from borges.runs.judged_ledger import JudgedLedger
from borges.runtime.stage_checkpoints import (
    CODED_KEY,
    PLAN_KEY,
    coded_payload,
    judged_payload,
    plan_payload,
)
from tests.runs.fakes import make_option, make_plan


def ledger() -> JudgedLedger:
    value = JudgedLedger()
    value.record("s1", make_option("a"), Judgement(defensibility=0.7, accepted=True, reason="ok"))
    return value


def test_judged_payload_lists_each_option_with_its_judgement() -> None:
    payload = judged_payload(ledger())
    [entry] = payload["s1"]
    assert entry["option"]["id"] == "a" and entry["judgement"]["defensibility"] == 0.7


def test_plan_and_coded_payloads_hold_the_stage_results() -> None:
    plan = make_plan()
    coding = CodingSummary(options=4, smoke_tested=4)
    planned = plan_payload(plan, ledger(), coding)
    assert planned["plan"]["question"] == "does it ship?"
    assert planned["coding"]["options"] == 4 and "s1" in planned["judged"]
    coded = coded_payload(plan, ledger(), coding, ["promoted b"])
    assert coded["smoke_notes"] == ["promoted b"] and coded["plan"] == planned["plan"]
    assert PLAN_KEY != CODED_KEY and PLAN_KEY.startswith("stage:")
