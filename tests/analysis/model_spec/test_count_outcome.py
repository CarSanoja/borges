from __future__ import annotations

from borges.analysis.coder import generate_checked
from borges.analysis.model_spec.count_outcome import (
    agree_count_specs,
    agreed_text,
    count_outcome_problems,
    transformed_sources,
    with_raw_count_outcome,
)
from borges.analysis.model_spec.render import render_code
from borges.analysis.models import (
    AnalysisPlan,
    ColumnProfile,
    DatasetProfile,
    DecisionRule,
    Option,
    Step,
)
from tests.analysis.fakes import FakeLLM
from tests.analysis.model_spec.data import make_spec

POISSON_TEXT = (
    "Regress np.expm1(outcome) if the outcome is log-transformed else outcome on masfem "
    "using statsmodels.GLM with family=Poisson(); use robust "
    "covariance; exponentiate coefficient for masfem to get IRR, then compute approximate "
    "marginal effect as (IRR - 1) * mean(np.expm1(outcome) if the outcome is log-transformed "
    "else outcome); extract estimate, 95% CI, and p-value."
)


def option(option_id: str, spec: str, default: bool = False, code: str | None = None) -> Option:
    return Option(
        id=option_id, label=option_id, rationale="r", spec=spec, is_default=default, code=code
    )


def hurricanes_plan(poisson_code: str | None = None) -> AnalysisPlan:
    columns = [
        ColumnProfile(name="alldeaths", dtype="int64", n_missing=0, n_unique=36),
        ColumnProfile(name="masfem", dtype="float64", n_missing=0, n_unique=40),
    ]
    return AnalysisPlan(
        question="Do feminine names kill more?",
        estimand="Additional deaths",
        decision_rule=DecisionRule(metric="mean_diff"),
        dataset=DatasetProfile(name="storms", n_rows=94, columns=columns),
        steps=[
            Step(
                id="transform",
                title="Transform deaths",
                kind="transform",
                description="d",
                produces=["outcome"],
                options=[
                    option(
                        "log1p",
                        "Create outcome = np.log1p(alldeaths); return DataFrame with outcome.",
                        True,
                    ),
                    option("raw", "Create outcome = alldeaths; return DataFrame with outcome."),
                ],
            ),
            Step(
                id="model",
                title="Model",
                kind="model",
                description="d",
                options=[
                    option("opt4a", "Regress outcome on masfem using OLS.", True),
                    option("opt4b", POISSON_TEXT, code=poisson_code),
                ],
            ),
        ],
    )


def test_a_transform_step_names_the_raw_column_it_is_built_from() -> None:
    plan = hurricanes_plan()
    assert transformed_sources(plan, plan.step("model"), ["outcome"]) == {"outcome": "alldeaths"}


def test_a_name_no_option_transforms_is_not_a_transformed_source() -> None:
    plan = hurricanes_plan()
    plan.step("transform").options = [plan.step("transform").option("raw")]
    assert transformed_sources(plan, plan.step("model"), ["outcome"]) == {}


def test_a_count_spec_on_the_transformed_outcome_goes_back_to_the_raw_count() -> None:
    sources = {"outcome": "alldeaths"}
    poisson = make_spec("poisson", outcome="outcome", exposure="masfem")
    assert with_raw_count_outcome(poisson, sources).outcome == "alldeaths"
    ols = make_spec("ols", outcome="outcome", exposure="masfem")
    assert with_raw_count_outcome(ols, sources).outcome == "outcome"


def test_a_count_spec_on_a_transformed_outcome_with_no_single_source_is_a_problem() -> None:
    sources: dict[str, str | None] = {"outcome": None}
    poisson = make_spec("poisson", outcome="outcome", exposure="masfem")
    assert "raw count column" in count_outcome_problems(poisson, sources)[0]
    assert count_outcome_problems(make_spec("ols", outcome="outcome"), sources) == []
    assert count_outcome_problems(make_spec("poisson", outcome="alldeaths"), sources) == []


def test_the_text_of_a_count_option_names_the_raw_count_it_fits() -> None:
    text = agreed_text(POISSON_TEXT, "alldeaths")
    assert "expm1" not in text and "log-transformed" not in text
    assert text.startswith("Regress alldeaths on masfem")
    assert "mean(alldeaths)" in text
    assert text.endswith("Fitted to the raw count alldeaths, not to a transformed outcome.")


def test_text_that_never_names_a_transformed_outcome_is_left_alone() -> None:
    plain = "GLM Poisson on alldeaths with masfem; reports the rate ratio."
    assert agreed_text(plain, "alldeaths") == plain


def test_the_plan_text_agrees_with_the_raw_count_the_code_fits() -> None:
    code = render_code(make_spec("poisson", outcome="alldeaths", exposure="masfem"))
    plan = hurricanes_plan(code)
    assert agree_count_specs(plan) == ["opt4b"]
    assert "Fitted to the raw count alldeaths" in plan.step("model").option("opt4b").spec
    assert plan.step("model").option("opt4a").spec == "Regress outcome on masfem using OLS."
    assert agree_count_specs(plan) == []


async def test_a_poisson_option_on_the_transformed_outcome_is_coded_on_the_raw_count() -> None:
    plan = hurricanes_plan()
    spec = {
        "supported": True,
        "family": "poisson",
        "outcome": "outcome",
        "exposure": "masfem",
        "cov_type": "HC3",
    }
    llm = FakeLLM({"coder:model.opt4b:spec": spec})
    step = plan.step("model")
    code, _, note = await generate_checked(llm, plan, step, step.option("opt4b"))
    assert note == "template: poisson"
    assert "endog = data['alldeaths']" in code and "endog = data['outcome']" not in code
