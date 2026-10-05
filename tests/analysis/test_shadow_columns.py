from __future__ import annotations

from borges.analysis.planner_validation import plan_shortfalls
from borges.analysis.shadow_columns import shadow_copies
from tests.analysis.fakes import make_profile
from tests.analysis.test_planner import popt, pstep
from tests.analysis.test_planner_breadth import broad

COLUMNS = {"balance", "campaign", "job"}
WINSOR = (
    "For columns ['balance', 'campaign'], clip at the 1st and 99th percentiles; write winsorized "
    "versions as 'balance_w', 'campaign_w'; return DataFrame with original and winsorized columns."
)


def test_a_changed_copy_under_a_new_name_is_a_shadow() -> None:
    assert shadow_copies(WINSOR, [], COLUMNS) == ["balance_w", "campaign_w"]
    capped = "Create a new column 'campaign_capped' = min(campaign, 10)."
    assert shadow_copies(capped, [], COLUMNS) == ["campaign_capped"]


def test_a_produced_name_an_indicator_or_a_column_is_not_a_shadow() -> None:
    assert shadow_copies(WINSOR, ["balance_w", "campaign_w"], COLUMNS) == []
    assert shadow_copies("Create 'job_missing' = 1 where 'job' is null.", [], COLUMNS) == []
    assert shadow_copies("Clip 'campaign' at 10 in place.", [], COLUMNS) == []


def test_the_planner_is_asked_to_change_the_column_in_place() -> None:
    out = broad()
    option = popt("winsor")
    option.spec = "Clip 'outcome' at its 99th percentile and write it as 'outcome_w'."
    out.steps[0] = pstep(out.steps[0].id, "filter", [*out.steps[0].options, option])
    [problem] = [p for p in plan_shortfalls(out.steps, make_profile()) if "copy" in p]
    assert f"{out.steps[0].id}.winsor: outcome_w" in problem and "in place" in problem
