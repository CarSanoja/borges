from __future__ import annotations

from borges.analysis.judge import judge_option
from borges.analysis.models import Option, Step
from borges.analysis.option_equivalence import equivalence_reason
from tests.analysis.fakes import FakeLLM, make_plan

BASELINE_CODE = """import statsmodels.formula.api as smf

def estimate(df, ctx):
    fit = smf.logit('subscribed ~ campaign + age', df).fit(disp=0)
    return {'estimate': fit.params['campaign']}
"""
RENAMED_CODE = """import statsmodels.formula.api as smf

def estimate(df, ctx):
    '''categorical exposure'''
    model = smf.logit('subscribed  ~  Campaign + age', df).fit(disp=0)
    return {'estimate': model.params['campaign']}
"""
DIFFERENT_CODE = BASELINE_CODE.replace("campaign + age", "C(campaign) + age")


def step_with(default: Option, other: Option) -> Step:
    return Step(id="m1", title="Estimator", kind="model", description="", options=[default, other])


def option(oid: str, label: str, spec: str, code: str | None = None, default: bool = False):
    return Option(id=oid, label=label, rationale="r", spec=spec, is_default=default, code=code)


def test_same_code_after_normalisation_is_a_duplicate() -> None:
    base = option("logit", "Logit", "logit of subscription on calls", BASELINE_CODE, True)
    other = option("adv_cat", "Categorical exposure", "calls as category", RENAMED_CODE)
    reason = equivalence_reason(step_with(base, other), other)
    assert reason is not None and "same estimator, covariates and sample filter" in reason


def test_different_covariates_are_not_a_duplicate() -> None:
    base = option("logit", "Logit", "logit of subscription on calls", BASELINE_CODE, True)
    other = option("adv_cat", "Categorical exposure", "calls as category", DIFFERENT_CODE)
    assert equivalence_reason(step_with(base, other), other) is None


def test_same_words_in_another_order_is_a_duplicate() -> None:
    base = option("logit", "Logistic regression", "Logistic regression of subscription", None, True)
    other = option("adv_x", "Regression, logistic", "Subscription of logistic regression", None)
    assert equivalence_reason(step_with(base, other), other) is not None


def test_distinct_options_pass() -> None:
    base = option("logit", "Logistic regression", "Logistic regression of subscription", None, True)
    other = option("adv_lpm", "Linear probability model", "OLS on the subscription indicator")
    assert equivalence_reason(step_with(base, other), other) is None


def test_the_default_itself_is_never_a_duplicate() -> None:
    base = option("logit", "Logit", "logit", BASELINE_CODE, True)
    other = option("adv_cat", "Cat", "cat", BASELINE_CODE)
    assert equivalence_reason(step_with(base, other), base) is None


async def test_judge_rejects_duplicates_without_a_model_call() -> None:
    plan = make_plan()
    step = plan.step("d1")
    default = step.default
    clone = Option(
        id="adv_keep_all",
        label=default.label,
        rationale="r",
        spec="something else",
        origin="adversary",
    )
    llm = FakeLLM({})
    judgement = await judge_option(llm, plan, step, clone)
    assert judgement.accepted is False and judgement.defensibility == 0.0
    assert judgement.reason.startswith("equivalent to the conventional option")
    assert llm.calls == []
