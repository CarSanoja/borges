from __future__ import annotations

import pytest

from borges.analysis.models import DecisionRule
from borges.analysis.planner import FRESH_KEY, plan_analysis
from borges.analysis.planner_degenerate import DEGENERATE, is_degenerate, loading_shortfall
from borges.analysis.schemas import PlannedOption, PlannedStep, PlannerOutput
from borges.llm.client import LLMError
from tests.analysis.fakes import FakeLLM, make_profile


def popt(option_id: str, spec: str = "s", default: bool = False) -> PlannedOption:
    return PlannedOption(
        id=option_id, label=option_id, rationale="r", spec=spec, is_default=default
    )


def pstep(step_id: str, kind: str, options: list[PlannedOption]) -> PlannedStep:
    produces = [f"{step_id}_col"] if kind in ("transform", "feature") else []
    return PlannedStep(
        id=step_id, title=step_id, kind=kind, description="d", options=options, produces=produces
    )


LOAD = "import pandas as pd; df = pd.read_csv('data.csv')"
NO_MODEL = PlannerOutput(
    estimand="Mean of Rel1",
    steps=[
        pstep("load", "transform", [popt("csv", LOAD, True)]),
        pstep("mean", "transform", [popt("m")]),
    ],
)
GOOD = PlannerOutput(
    estimand="E",
    steps=[
        pstep("f1", "filter", [popt("a", default=True), popt("b")]),
        pstep("m", "model", [popt("ols", default=True), popt("welch")]),
    ],
)


async def plan_with(responses: dict) -> tuple[FakeLLM, object]:
    llm = FakeLLM(responses)
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    return llm, plan


def test_a_plan_without_a_model_step_or_that_loads_files_is_degenerate() -> None:
    assert is_degenerate(NO_MODEL.steps)
    loads = [pstep("f1", "filter", [popt("a", LOAD)]), *GOOD.steps[1:]]
    assert is_degenerate(loads) and not is_degenerate(GOOD.steps)


def test_loading_options_are_named_in_the_shortfall() -> None:
    found = loading_shortfall(NO_MODEL.steps)
    assert found is not None and "load.csv" in found and "arrives in df" in found
    assert loading_shortfall(GOOD.steps) is None


async def test_a_degenerate_plan_is_drawn_again_from_scratch() -> None:
    llm, plan = await plan_with({"planner": NO_MODEL, FRESH_KEY: GOOD})
    assert [s.id for s in plan.steps] == ["f1", "m"]
    assert FRESH_KEY in [c.key for c in llm.calls]
    fresh = next(c for c in llm.calls if c.key == FRESH_KEY)
    assert fresh.messages == llm.calls[0].messages


async def test_a_plan_still_degenerate_after_the_fresh_draw_fails_the_run() -> None:
    with pytest.raises(LLMError, match="fresh plan"):
        await plan_with({"planner": NO_MODEL, FRESH_KEY: NO_MODEL})
    assert "no model step" in DEGENERATE


async def test_a_sound_plan_is_never_drawn_again() -> None:
    llm, _ = await plan_with({"planner": GOOD})
    assert not any(c.key.startswith(FRESH_KEY) for c in llm.calls)


async def test_a_fresh_draw_that_fails_keeps_the_clear_reason() -> None:
    with pytest.raises(LLMError, match="fresh plan has no model step"):
        await plan_with({"planner": NO_MODEL})
