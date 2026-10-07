from __future__ import annotations

from borges.analysis.models import AnalysisPlan, DecisionRule
from borges.analysis.planner import plan_analysis
from borges.analysis.planner_fidelity import UNCHECKED
from borges.analysis.schemas import PlannerOutput
from borges.llm.client import Role
from borges.runs.pipeline_caveats import analysis_caveats
from tests.analysis.fakes import FakeLLM, make_profile
from tests.analysis.test_planner import popt, pstep

RULE = DecisionRule(metric="m")
ANALYSIS = "single = Relationship 1 or 2, committed = 3 or 4; OLS"
MISMATCH = {
    "mismatches": [
        {
            "step_id": "code",
            "analysis_part": "single = Relationship 1 or 2",
            "default_spec": "committed if Relationship in {2,3,4}",
            "differs": True,
            "problem": "Relationship 2 is coded committed",
        }
    ]
}
MATCH = {
    "mismatches": [
        {
            "step_id": "m",
            "analysis_part": "OLS",
            "default_spec": "fit OLS",
            "differs": False,
            "problem": "Matches analysis.",
        }
    ]
}


def output(default: str) -> PlannerOutput:
    return PlannerOutput(
        estimand="E",
        steps=[
            pstep("code", "feature", [popt("r2", default == "r2"), popt("r1", default == "r1")]),
            pstep("m", "model", [popt("ols", True), popt("hc3")]),
        ],
    )


async def plan(responses: dict, analysis: str = ANALYSIS) -> tuple[FakeLLM, AnalysisPlan]:
    llm = FakeLLM(responses)
    return llm, await plan_analysis(llm, make_profile(), "Q?", RULE, analysis)


async def test_a_faithful_plan_is_checked_once_by_the_judge_model() -> None:
    llm, result = await plan({"planner": output("r1"), "fidelity:1": {"mismatches": []}})
    [check] = [c for c in llm.calls if c.key == "fidelity:1"]
    assert check.role is Role.JUDGE and ANALYSIS in check.messages[-1]["content"]
    assert result.step("code").default.id == "r1" and result.analysis_gaps == []


async def test_parts_the_checker_lists_as_matching_are_not_mismatches() -> None:
    llm, result = await plan({"planner": output("r1"), "fidelity:1": MATCH})
    assert "planner:fidelity1" not in [c.key for c in llm.calls]
    assert result.analysis_gaps == []


async def test_a_mismatch_is_sent_back_to_the_planner_and_the_fixed_plan_is_kept() -> None:
    llm, result = await plan(
        {
            "planner": output("r2"),
            "fidelity:1": MISMATCH,
            "planner:fidelity1": output("r1"),
            "fidelity:2": {"mismatches": []},
        }
    )
    [retry] = [c for c in llm.calls if c.key == "planner:fidelity1"]
    assert "Relationship 2 is coded committed" in retry.messages[-1]["content"]
    assert result.step("code").default.id == "r1" and result.analysis_gaps == []


async def test_a_mismatch_that_survives_two_retries_is_reported() -> None:
    llm, result = await plan(
        {
            "planner": output("r2"),
            "planner:fidelity1": output("r2"),
            "planner:fidelity2": output("r2"),
            **{f"fidelity:{n}": MISMATCH for n in (1, 2, 3)},
        }
    )
    asked = [c.key for c in llm.calls]
    assert "fidelity:4" not in asked and "planner:fidelity3" not in asked
    [gap] = result.analysis_gaps
    assert "the analysis says 'single = Relationship 1 or 2'" in gap
    [caveat] = analysis_caveats(result)
    assert caveat.startswith("The starting point may not be exactly your analysis")


async def test_a_failed_check_says_the_plan_was_not_checked() -> None:
    _, result = await plan({"planner": output("r1")})
    [gap] = result.analysis_gaps
    assert gap.startswith(UNCHECKED)


async def test_without_an_analysis_nothing_is_checked() -> None:
    llm, result = await plan({"planner": output("r2")}, analysis="")
    assert not [c.key for c in llm.calls if c.key.startswith("fidelity")]
    assert result.analysis_gaps == []
