from __future__ import annotations

from borges.analysis.model_spec.validate_ctx import ctx_problems
from tests.analysis.model_spec.data import make_spec

CTX = ["age", "gender", "ses"]


def test_a_covariate_chosen_by_the_covariate_step_is_not_repeated() -> None:
    spec = make_spec("ols", covariates=["age", "income"], covariates_from_ctx=True)
    [problem] = ctx_problems(spec, CTX, "OLS on x and covariates from ctx['covariates']")
    assert problem.startswith("'age' is chosen by the covariate step")


def test_an_option_that_reads_ctx_must_say_so_in_the_spec() -> None:
    spec = make_spec("ols", covariates=["age"])
    [problem] = ctx_problems(spec, CTX, "Regress y on x and ctx['covariates'] with HC2")
    assert "covariates_from_ctx" in problem


def test_a_clean_spec_passes() -> None:
    spec = make_spec("ols", covariates=["income"], covariates_from_ctx=True)
    assert ctx_problems(spec, CTX, "OLS on x, income and ctx['covariates']") == []
    assert ctx_problems(make_spec("ols", covariates=["age"]), [], "OLS on x and age") == []
