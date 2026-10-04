from __future__ import annotations

from borges.analysis.models import DecisionRule
from borges.analysis.planner import plan_analysis
from borges.analysis.planner_products import drop_renamed, renamed_products
from borges.analysis.schemas import PlannedOption, PlannerOutput
from tests.analysis.fakes import FakeLLM, make_profile
from tests.analysis.test_planner import popt, pstep


def option(option_id: str, spec: str, default: bool = False) -> PlannedOption:
    return PlannedOption(
        id=option_id, label=option_id, rationale="r", spec=spec, is_default=default
    )


def transform_plan() -> PlannerOutput:
    transform = pstep(
        "t",
        "transform",
        [
            option("log", "Create new column 'log_outcome' = log1p(outcome).", True),
            option("sqrt", "Create new column 'sqrt_outcome' = np.sqrt(outcome)."),
            option("raw", "Return the DataFrame unchanged."),
        ],
        produces=["log_outcome"],
    )
    return PlannerOutput(
        estimand="E",
        steps=[
            pstep("trim", "filter", [popt("a", True), popt("b")]),
            transform,
            pstep("c", "feature", [popt("a", True), popt("b")]),
            pstep("m", "model", [popt("ols", True), popt("welch")]),
        ],
    )


def test_an_option_that_builds_its_own_column_name_is_found() -> None:
    assert renamed_products(transform_plan().steps, make_profile()) == {"t": ["sqrt"]}


async def test_the_planner_is_asked_to_fix_it_and_the_option_is_dropped_if_it_does_not() -> None:
    llm = FakeLLM({"planner": transform_plan(), "planner:retry": transform_plan()})
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    assert [o.id for o in plan.step("t").options] == ["log", "raw"]
    retry = llm.calls[1].messages[-1]["content"]
    assert "builds its result under its own column name" in retry and "t: sqrt" in retry


def test_options_that_each_build_another_produced_name_are_found() -> None:
    step = pstep(
        "t",
        "transform",
        [
            option("log", "Create new column 'log_outcome' = log1p(outcome).", True),
            option("binary", "Create new column 'any_outcome' = outcome > 0."),
            option("both", "Create 'log_outcome' and 'any_outcome'."),
        ],
        produces=["log_outcome", "any_outcome"],
    )
    plan = transform_plan()
    steps = [plan.steps[0], step, *plan.steps[2:]]
    assert renamed_products(steps, make_profile()) == {"t": ["binary"]}
    kept = drop_renamed(steps, make_profile())[1]
    assert [o.id for o in kept.options] == ["log", "both"] and kept.produces == ["log_outcome"]
