from __future__ import annotations

import pytest

from borges.analysis.models import DecisionRule
from borges.analysis.planner import plan_analysis, produced_name, step_produces
from borges.analysis.schemas import PlannedOption, PlannedStep, PlannerOutput
from borges.llm.client import LLMError, Role
from tests.analysis.fakes import FakeLLM, make_profile


def popt(option_id: str, default: bool = False) -> PlannedOption:
    return PlannedOption(id=option_id, label=option_id, rationale="r", spec="s", is_default=default)


def pstep(
    step_id: str,
    kind: str,
    options: list[PlannedOption],
    produces: list[str] | None = None,
) -> PlannedStep:
    if produces is None:
        produces = [f"{step_id}_col"] if kind in ("transform", "feature") else []
    return PlannedStep(
        id=step_id,
        title=step_id,
        kind=kind,
        description="d",
        options=options,
        produces=produces,
    )


async def run(output: PlannerOutput) -> tuple[FakeLLM, object]:
    llm = FakeLLM({"planner": output})
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    return llm, plan


async def test_builds_plan_and_calls_planner() -> None:
    out = PlannerOutput(
        estimand="E",
        steps=[
            pstep("f1", "filter", [popt("a", True), popt("b")]),
            pstep("m", "model", [popt("ols", True), popt("welch")]),
        ],
    )
    llm, plan = await run(out)
    assert plan.estimand == "E" and plan.question == "Q?"
    assert [s.id for s in plan.steps] == ["f1", "m"]
    assert all(o.origin == "planner" for s in plan.steps for o in s.options)
    call = llm.calls[0]
    assert call.role is Role.PLANNER and call.key == "planner" and call.max_tokens == 4096
    assert call.schema is PlannerOutput
    assert "group" in call.messages[1]["content"]


async def test_fixes_defaults() -> None:
    out = PlannerOutput(
        estimand="E",
        steps=[
            pstep("f1", "filter", [popt("a", True), popt("b", True)]),
            pstep("f2", "filter", [popt("a"), popt("b")]),
            pstep("m", "model", [popt("ols", True)]),
        ],
    )
    _, plan = await run(out)
    assert [o.is_default for o in plan.steps[0].options] == [True, False]
    assert [o.is_default for o in plan.steps[1].options] == [True, False]


async def test_unique_ids() -> None:
    out = PlannerOutput(
        estimand="E",
        steps=[
            pstep("f", "filter", [popt("a", True), popt("a")]),
            pstep("f", "filter", [popt("x", True)]),
            pstep("m", "model", [popt("ols", True)]),
        ],
    )
    _, plan = await run(out)
    assert [s.id for s in plan.steps] == ["f", "f_2", "m"]
    assert [o.id for o in plan.steps[0].options] == ["a", "a_2"]


async def test_model_step_moved_last() -> None:
    out = PlannerOutput(
        estimand="E",
        steps=[
            pstep("m", "model", [popt("ols", True)]),
            pstep("f", "filter", [popt("a", True)]),
        ],
    )
    _, plan = await run(out)
    assert [s.id for s in plan.steps] == ["f", "m"]
    assert plan.steps[-1].kind == "model"


async def test_no_model_step_raises() -> None:
    out = PlannerOutput(estimand="E", steps=[pstep("f", "filter", [popt("a", True)])])
    with pytest.raises(LLMError):
        await run(out)


async def test_plan_carries_the_scale_derived_from_the_metric() -> None:
    out = PlannerOutput(
        estimand="E",
        steps=[pstep("m", "model", [popt("ols", True), popt("welch")])],
    )
    for metric, scale in [("lift (percentage points)", 100.0), ("standardised coefficient", 1.0)]:
        llm = FakeLLM({"planner": out})
        plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric=metric))
        assert plan.result_scale == scale


@pytest.mark.parametrize(
    "raw",
    [
        "ctx|covariates",
        "ctx['covariates']",
        'ctx["covariates"]',
        "ctx.covariates",
        "ctx:covariates",
        "ctx.get('covariates', [])",
        " covariates ",
        "ctx['covariates",
    ],
)
def test_produces_written_as_a_ctx_reference_is_the_bare_key(raw: str) -> None:
    assert produced_name(raw) == "covariates"


def test_produces_that_only_starts_with_ctx_is_left_alone() -> None:
    assert produced_name("ctx_score") == "ctx_score"


def covariate_step(produces: list[str], *specs: str) -> PlannedStep:
    options = [
        PlannedOption(id=f"o{i}", label=f"o{i}", rationale="r", spec=spec, is_default=i == 0)
        for i, spec in enumerate(specs)
    ]
    return PlannedStep(
        id="cov", title="t", kind="feature", description="d", options=options, produces=produces
    )


def test_a_bare_ctx_produces_names_the_keys_every_option_writes() -> None:
    step = covariate_step(
        ["ctx"],
        "Set ctx['covariates'] = ['age']; ctx['label'] = 'a'.",
        "Set ctx['covariates'] = ['age', 'job']; return the frame unchanged.",
    )
    assert step_produces(step) == ["covariates"]


def test_a_bare_ctx_produces_without_shared_writes_is_dropped() -> None:
    step = covariate_step(["ctx", "score"], "Write df['score'].", "Write df['score'].")
    assert step_produces(step) == ["score"]
