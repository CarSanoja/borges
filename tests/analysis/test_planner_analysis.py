from __future__ import annotations

from borges.analysis.models import DecisionRule
from borges.analysis.planner import plan_analysis
from borges.analysis.prompts.planner import analysis_block, build_messages
from borges.analysis.schemas import PlannerOutput
from tests.analysis.fakes import FakeLLM, make_profile
from tests.analysis.test_planner import popt, pstep

RULE = DecisionRule(metric="m")


def test_no_analysis_adds_nothing_to_the_planner_message() -> None:
    assert analysis_block("  ") == ""
    plain = build_messages(make_profile(), "Q?", RULE)
    assert plain == build_messages(make_profile(), "Q?", RULE, "")


def test_the_users_analysis_is_the_default_path_implemented_as_written() -> None:
    user = build_messages(make_profile(), "Q?", RULE, "OLS of y on x, days 7-14")[-1]["content"]
    assert "The user's own analysis" in user and "OLS of y on x, days 7-14" in user
    assert "default option of every step it decides, implemented exactly as written" in user


async def test_the_plan_carries_the_users_analysis() -> None:
    output = PlannerOutput(
        estimand="e",
        steps=[pstep("m", "model", [popt("ols", True), popt("logit")])],
    )
    llm = FakeLLM({"planner": output})
    plan = await plan_analysis(llm, make_profile(), "Q?", RULE, "OLS of y on x")
    assert plan.analysis == "OLS of y on x"
    assert "OLS of y on x" in llm.calls[0].messages[-1]["content"]


def test_a_difference_keeps_the_direction_the_analysis_gives_it() -> None:
    """fertility_vote on 7 October, run 15: 'the days from DateTesting to the next onset' was
    planned as DateTesting minus the onset, every cycle day became 28, the window filter kept no
    woman and the run failed; the fidelity check had not looked at the direction."""
    from borges.analysis.planner_fidelity import SYSTEM

    assert "'the days from A to B' is B minus A" in analysis_block("cycle day = 28 minus ...")
    assert '"the days from A to B" is B minus A' in SYSTEM
