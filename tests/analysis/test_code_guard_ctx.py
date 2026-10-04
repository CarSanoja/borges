from __future__ import annotations

from borges.analysis.code_guard_ctx import ctx_read_violations, varying_ctx_keys
from borges.analysis.models import AnalysisPlan, Option, Step
from tests.analysis.fakes import make_plan


def option(option_id: str, spec: str) -> Option:
    return Option(id=option_id, label=option_id, rationale="r", spec=spec, is_default=False)


def step(step_id: str, title: str, kind: str, *specs: str) -> Step:
    options = [option(f"{step_id}{i}", s) for i, s in enumerate(specs)]
    options[0].is_default = True
    return Step(id=step_id, title=title, kind=kind, description="d", options=options)


COVARIATES = step(
    "cov",
    "Covariates",
    "feature",
    "ctx['covariates'] = []",
    "ctx['covariates'] = ['platform', 'day']",
)
OUTCOME = step(
    "wb",
    "Wellbeing outcome",
    "feature",
    "ctx['outcome'] = 'wb_overall'",
    "ctx['outcome'] = 'wb_psych'",
)
MODEL = step("m", "Model", "model", "OLS of y on x")


def plan(*steps: Step) -> AnalysisPlan:
    return make_plan().model_copy(update={"steps": list(steps)})


def test_keys_that_differ_across_options_of_an_earlier_step_are_found() -> None:
    keys = varying_ctx_keys(plan(COVARIATES, OUTCOME, MODEL), MODEL)
    assert keys == {"covariates": "Covariates", "outcome": "Wellbeing outcome"}


def test_a_key_read_by_an_intermediate_step_is_not_the_model_s_concern() -> None:
    reader = step("t", "Transform", "transform", "df['y'] = df[ctx['outcome']]")
    assert varying_ctx_keys(plan(OUTCOME, reader, MODEL), MODEL) == {}


def test_code_that_ignores_a_varying_key_is_refused() -> None:
    code = "def estimate(df, ctx):\n    names = []\n    return names\n"
    [problem] = ctx_read_violations(code, {"covariates": "Covariates"}, "OLS clustered by user")
    assert "never reads it" in problem and "ctx.get('covariates')" in problem


def test_code_that_reads_the_key_or_an_unadjusted_option_passes() -> None:
    reads = "def estimate(df, ctx):\n    return ctx.get('covariates', [])\n"
    assert ctx_read_violations(reads, {"covariates": "Covariates"}, "OLS") == []
    ignores = "def estimate(df, ctx):\n    return 1\n"
    assert ctx_read_violations(ignores, {"covariates": "C"}, "Unadjusted difference") == []


def test_a_write_alone_does_not_count_as_a_read() -> None:
    code = "def estimate(df, ctx):\n    ctx['outcome'] = 'y'\n    return 1\n"
    assert ctx_read_violations(code, {"outcome": "O"}, "OLS")


def test_a_key_whose_values_are_labels_not_columns_is_ignored() -> None:
    labels = step(
        "sk",
        "Skin tone",
        "transform",
        "ctx['skin_tone'] = 'mean_0.5'",
        "ctx['skin_tone'] = 'max_0.5'",
    )
    data = step("pc", "Norms", "transform", "ctx['cnorms'] = pc1.tolist()", "df['c'] = 1")
    assert varying_ctx_keys(plan(labels, data, MODEL), MODEL) == {}


def test_a_key_whose_values_name_columns_counts() -> None:
    chosen = step(
        "ex", "Exposure", "feature", "ctx['x_col'] = 'treatment'", "ctx['x_col'] = 'score'"
    )
    current = plan(chosen, MODEL)
    current.dataset.columns[0].name = "treatment"
    current.dataset.columns[1].name = "score"
    assert varying_ctx_keys(current, MODEL) == {"x_col": "Exposure"}
