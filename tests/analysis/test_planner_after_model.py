from __future__ import annotations

from borges.analysis.models import DecisionRule
from borges.analysis.planner import plan_analysis
from borges.analysis.planner_validation import plan_shortfalls
from borges.analysis.schemas import PlannerOutput
from tests.analysis.fakes import FakeLLM, make_profile
from tests.analysis.test_planner import popt, pstep


def formats_after_model() -> PlannerOutput:
    late = pstep("final_output", "transform", [popt("format", True), popt("raw")])
    late = late.model_copy(update={"produces": ["odds_ratio", "ci_low", "ci_high", "p_value"]})
    return PlannerOutput(
        estimand="E",
        steps=[
            pstep("trim", "filter", [popt("a", True), popt("b")]),
            pstep("scale", "transform", [popt("a", True), popt("b")]),
            pstep("m", "model", [popt("ols", True), popt("welch")]),
            late,
        ],
    )


def test_a_step_after_the_model_is_a_shortfall() -> None:
    problems = plan_shortfalls(formats_after_model().steps, make_profile())
    assert any("come after the model step" in p and "final_output" in p for p in problems)


async def test_a_step_left_after_the_model_is_dropped_instead_of_run_before_it() -> None:
    llm = FakeLLM({"planner": formats_after_model(), "planner:retry": formats_after_model()})
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    assert [s.id for s in plan.steps] == ["trim", "scale", "m"]
    assert "come after the model step" in llm.calls[1].messages[-1]["content"]
