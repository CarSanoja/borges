from __future__ import annotations

from borges.analysis.code_guard_produces import products_read_violations, unused_products
from borges.analysis.models import AnalysisPlan, Step
from tests.analysis.fakes import make_plan
from tests.analysis.test_code_guard_ctx import step

RELIGIOSITY = step(
    "rel",
    "Religiosity score",
    "transform",
    "Compute religiosity as the mean of rel_1..rel_9; write ctx['religiosity'] = 'religiosity'.",
    "Compute religiosity as the oriented first principal component of rel_1..rel_9.",
).model_copy(update={"produces": ["religiosity"]})
MODEL = step("m", "Model", "model", "OLS of wellbeing on religiosity")

REBUILT = """
def estimate(df, ctx):
    items = df[['rel_1', 'rel_2']]
    score = items.mean(axis=1)
    return score
"""
READS_COLUMN = "def estimate(df, ctx):\n    x = df['religiosity']\n"
READS_CTX = "def estimate(df, ctx):\n    x = df[ctx['religiosity']]\n"


def plan(*steps: Step) -> AnalysisPlan:
    return make_plan().model_copy(update={"steps": list(steps)})


def test_a_model_that_rebuilds_an_earlier_product_is_refused() -> None:
    products = unused_products(plan(RELIGIOSITY, MODEL), MODEL)
    problems = products_read_violations(REBUILT, products)
    assert len(problems) == 1
    assert "'Religiosity score'" in problems[0] and "'religiosity'" in problems[0]


def test_a_model_that_reads_the_product_passes() -> None:
    products = unused_products(plan(RELIGIOSITY, MODEL), MODEL)
    assert products_read_violations(READS_COLUMN, products) == []
    assert products_read_violations(READS_CTX, products) == []


def test_a_product_read_by_an_intermediate_step_is_not_required() -> None:
    zscore = step("z", "Standardise", "transform", "Write rel_z = z-score of religiosity.")
    assert unused_products(plan(RELIGIOSITY, zscore, MODEL), MODEL) == {}


def test_a_ctx_key_that_carries_the_product_name_counts_as_a_read() -> None:
    carrier = step(
        "rel",
        "Religiosity score",
        "transform",
        "Write df['rel_mean'] and ctx['exposure'] = 'rel_mean'.",
        "Write df['rel_pc'] and ctx['exposure'] = 'rel_pc'.",
    ).model_copy(update={"produces": ["rel_mean", "rel_pc"]})
    products = unused_products(plan(carrier, MODEL), MODEL)
    code = "def estimate(df, ctx):\n    x = df[ctx['exposure']]\n"
    assert products_read_violations(code, products) == []


def test_a_single_option_step_or_a_ctx_key_step_is_left_to_other_checks() -> None:
    single = RELIGIOSITY.model_copy(update={"options": RELIGIOSITY.options[:1]})
    covariates = step(
        "c", "Covariates", "feature", "ctx['covariates'] = []", "ctx['covariates'] = ['a']"
    )
    covariates = covariates.model_copy(update={"produces": ["covariates"]})
    assert unused_products(plan(single, covariates, MODEL), MODEL) == {}
