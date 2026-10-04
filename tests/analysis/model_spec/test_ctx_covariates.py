from __future__ import annotations

from borges.analysis.model_spec.ctx_covariates import ctx_covariate_names
from borges.analysis.models import AnalysisPlan, DatasetProfile, DecisionRule, Option, Step

AVAILABLE = ["x", "player", "cat", "y"]


def plan_with(code: str | None, spec: str) -> tuple[AnalysisPlan, Step]:
    option = Option(id="o", label="l", rationale="r", spec=spec, is_default=True, code=code)
    adjust = Step(id="adjust", title="t", kind="feature", description="d", options=[option])
    model = Step(id="model", title="t", kind="model", description="d", options=[])
    plan = AnalysisPlan(
        question="q",
        estimand="e",
        decision_rule=DecisionRule(metric="m"),
        dataset=DatasetProfile(name="t", n_rows=1, columns=[]),
        steps=[adjust, model],
    )
    return plan, model


def test_literal_list_assigned_to_ctx_is_read_from_code() -> None:
    code = "def apply(df, ctx):\n    ctx['covariates'] = ['cat', 'player']\n    return df\n"
    plan, model = plan_with(code, "none")
    assert ctx_covariate_names(plan, model, AVAILABLE) == ["cat", "player"]


def test_variable_assigned_to_ctx_is_followed() -> None:
    code = 'def apply(df, ctx):\n    names = ["player"]\n    ctx["covariates"] = names\n'
    plan, model = plan_with(code, "none")
    assert ctx_covariate_names(plan, model, AVAILABLE) == ["player"]


def test_uncoded_options_are_read_from_their_spec() -> None:
    plan, model = plan_with(None, "write player and cat to ctx['covariates']")
    assert ctx_covariate_names(plan, model, AVAILABLE) == ["cat", "player"]


def test_steps_that_do_not_mention_covariates_contribute_nothing() -> None:
    plan, model = plan_with(None, "winsorize y at the 1st percentile; player stays")
    assert ctx_covariate_names(plan, model, AVAILABLE) == []
