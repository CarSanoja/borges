from __future__ import annotations

from borges.analysis.models import Judgement, Option
from borges.runs.judged_ledger import JudgedLedger, duplicate_in_plan
from tests.runs.fakes import make_option, make_plan


def relabelled(option_id: str, label: str) -> Option:
    return make_option(option_id).model_copy(update={"label": label})


def test_find_matches_within_the_same_step_only() -> None:
    ledger = JudgedLedger()
    ledger.record(
        "s1",
        relabelled("alt_z", "Z mean"),
        Judgement(defensibility=0.2, accepted=False, reason="r"),
    )
    assert ledger.find("s1", relabelled("adv_z", "Use Z mean as outcome")) is not None
    assert ledger.find("s2", relabelled("adv_z", "Use Z mean as outcome")) is None
    assert ledger.find("s1", make_option("other")) is None
    assert ledger.find("s1", relabelled("adv_z", "Something else")) is None


def test_duplicate_in_plan_finds_stripped_id() -> None:
    plan = make_plan()
    assert duplicate_in_plan(plan, "s2", relabelled("adv_y", "Label y again")) is not None
    assert duplicate_in_plan(plan, "s2", make_option("adv_q")) is None
