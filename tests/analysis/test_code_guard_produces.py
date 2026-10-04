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


def test_a_step_whose_options_also_impute_or_drop_rows_is_not_required() -> None:
    missing = step(
        "miss",
        "Handle missing values",
        "transform",
        "Create job_missing = 1 when job is null, then fill job with 'missing'.",
        "Fill nulls in job with its mode; no new columns.",
        "Drop rows where job is null.",
    ).model_copy(update={"produces": ["job_missing"]})
    assert unused_products(plan(missing, MODEL), MODEL) == {}


def checkout_plan() -> AnalysisPlan:
    from borges.analysis.models import ColumnProfile

    winsorize = step(
        "w",
        "Winsorize session duration",
        "transform",
        "Cap session_seconds at its 1st and 99th percentiles; write session_seconds_w.",
        "Copy session_seconds to session_seconds_w without modification.",
    ).model_copy(update={"produces": ["session_seconds_w"]})
    base = plan(winsorize, MODEL)
    names = ["converted", "variant", "session_seconds", "rel_1", "rel_2", "rel_3"]
    columns = [ColumnProfile(name=n, dtype="float64", n_missing=0, n_unique=9) for n in names]
    return base.model_copy(update={"dataset": base.dataset.model_copy(update={"columns": columns})})


def test_a_model_that_touches_neither_the_product_nor_its_source_is_not_refused() -> None:
    products = unused_products(checkout_plan(), MODEL)
    assert products["Winsorize session duration"][2] == {"session_seconds"}
    code = "def estimate(df, ctx):\n    y, x = df['converted'], df['variant']\n"
    assert products_read_violations(code, products) == []


def test_a_model_that_reads_the_raw_source_of_a_product_is_refused() -> None:
    products = unused_products(checkout_plan(), MODEL)
    code = "def estimate(df, ctx):\n    y, x = df['converted'], df[['session_seconds']]\n"
    assert len(products_read_violations(code, products)) == 1


def test_numbered_items_named_as_a_range_all_count_as_sources() -> None:
    base = checkout_plan()
    scored = base.model_copy(update={"steps": [RELIGIOSITY, MODEL]})
    products = unused_products(scored, MODEL)
    assert products["Religiosity score"][2] == {"rel_1", "rel_2", "rel_3"}
    code = "def estimate(df, ctx):\n    score = df[['rel_2', 'rel_3']].mean(axis=1)\n"
    assert len(products_read_violations(code, products)) == 1
