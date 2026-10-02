from __future__ import annotations

from borges.analysis.models import Judgement
from borges.runs.judged_ledger import JudgedLedger, duplicate_in_plan
from tests.runs.fakes import make_option, make_plan


def test_find_matches_within_the_same_step_only() -> None:
    ledger = JudgedLedger()
    ledger.record(
        "s1", make_option("alt_z"), Judgement(defensibility=0.2, accepted=False, reason="r")
    )
    assert ledger.find("s1", make_option("adv_z")) is not None
    assert ledger.find("s2", make_option("adv_z")) is None
    assert ledger.find("s1", make_option("other")) is None


def test_duplicate_in_plan_finds_stripped_id() -> None:
    plan = make_plan()
    assert duplicate_in_plan(plan, "s2", make_option("adv_y")) is not None
    assert duplicate_in_plan(plan, "s2", make_option("adv_q")) is None
