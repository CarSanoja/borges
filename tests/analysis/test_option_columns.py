from __future__ import annotations

from borges.analysis.models import Option
from borges.analysis.option_columns import missing_columns, missing_reason
from tests.garden.synthetic import option, plan_of, step_of

PLAN = plan_of(
    step_of("adjust", "feature", option("base", True)),
    notes={"rate_marriage": "", "age": "", "Educ": "", "pop": ""},
)


def proposed(spec: str) -> Option:
    return option("adv").model_copy(update={"spec": spec, "origin": "adversary"})


def test_covariates_that_are_not_in_the_data_are_named() -> None:
    spec = "ctx['covariates'] = ['rate_marriage', 'age', 'selfesteem', 'depression']"
    assert missing_columns(PLAN, proposed(spec)) == ["selfesteem", "depression"]
    assert missing_reason(PLAN, proposed(spec)) == (
        "names columns not in the data: selfesteem, depression"
    )


def test_terms_built_from_known_columns_are_not_invented() -> None:
    spec = (
        "ctx['covariates'] = ['I(age**2)', 'age:educ', 'age_sq', 'age2', 'log_rate_marriage', "
        "'wage_index']"
    )
    assert missing_columns(PLAN, proposed(spec)) == ["wage_index"]


def test_names_match_whatever_their_case() -> None:
    spec = "Set ctx['covariates'] = ['EDUC', 'Age']; return df"
    assert missing_columns(PLAN, proposed(spec)) == []


def test_a_column_another_option_creates_is_known() -> None:
    plan = plan_of(
        step_of("dummies", "feature", option("d", True, code="df['platform_ios'] = 1")),
        notes={"age": ""},
    )
    assert missing_columns(plan, proposed("ctx['covariates'] = ['platform_ios']")) == []


def test_prose_without_a_column_list_is_left_alone() -> None:
    assert missing_reason(PLAN, proposed("Winsorize the outcome at the 95th percentile")) is None


def test_weights_naming_a_missing_column_are_rejected() -> None:
    reason = missing_reason(PLAN, proposed("WLS weighted by 'sample_weight'"))
    assert reason == "names columns not in the data: sample_weight"


def test_population_weights_without_a_weight_column_are_rejected() -> None:
    plan = plan_of(step_of("m", "model", option("ols", True)), notes={"murder": "", "poverty": ""})
    reason = missing_reason(plan, proposed("WLS with population weights"))
    assert reason == "promises weights but the data has no weight column"
    assert missing_reason(PLAN, proposed("WLS with population weights")) is None
