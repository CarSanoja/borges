from __future__ import annotations

from borges.analysis.model_spec.ctx_reader import reading_ctx_covariates
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import AnalysisPlan, DatasetProfile, DecisionRule, Option, Step


def plan_with(spec: str) -> tuple[AnalysisPlan, Step, Option]:
    adjust = Option(id="a", label="l", rationale="r", spec=spec, is_default=True)
    fit = Option(id="m", label="OLS", rationale="r", spec="regress y on tool", is_default=True)
    steps = [
        Step(
            id="adjust",
            title="No covariate adjustment",
            kind="feature",
            description="d",
            options=[adjust],
        ),
        Step(id="model", title="t", kind="model", description="d", options=[fit]),
    ]
    plan = AnalysisPlan(
        question="q",
        estimand="e",
        decision_rule=DecisionRule(metric="m"),
        dataset=DatasetProfile(name="t", n_rows=1, columns=[]),
        steps=steps,
    )
    return plan, steps[1], fit


def spec() -> ModelSpecOutput:
    return ModelSpecOutput.model_validate(
        {"supported": True, "family": "ols", "outcome": "y", "exposure": "tool"}
    )


def test_an_empty_list_in_ctx_is_still_read_so_a_later_adjustment_reaches_the_model() -> None:
    plan, step, option = plan_with("Set ctx['covariates'] = [] (empty list).")
    assert reading_ctx_covariates(spec(), plan, step, option.spec).covariates_from_ctx


def test_an_option_that_says_it_is_unadjusted_keeps_its_own_list() -> None:
    plan, step, option = plan_with("Set ctx['covariates'] = [] (empty list).")
    found = reading_ctx_covariates(spec(), plan, step, "unadjusted OLS of y on tool")
    assert not found.covariates_from_ctx


def test_no_earlier_step_writing_covariates_leaves_the_spec_alone() -> None:
    plan, step, option = plan_with("winsorize y at the 99th percentile")
    assert not reading_ctx_covariates(spec(), plan, step, option.spec).covariates_from_ctx
