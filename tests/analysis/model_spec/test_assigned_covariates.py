from __future__ import annotations

from borges.analysis.model_spec.assigned_covariates import (
    unbuilt_covariates,
    with_assigned_covariates,
)
from borges.analysis.models import Option
from tests.analysis.model_spec.data import make_spec

WINSORIZED = (
    "Set ctx['covariates'] = ['winsorized_session_seconds']; where winsorized_session_seconds is "
    "computed as session_seconds winsorized at the 5th and 95th percentiles; return the input "
    "DataFrame unchanged."
)
AVAILABLE = ["converted", "variant", "platform", "session_seconds"]


def option(spec: str) -> Option:
    return Option(
        id="o", label="OLS with winsorized session length covariate", rationale="r", spec=spec
    )


def test_a_covariate_the_data_lacks_goes_to_free_code() -> None:
    assert unbuilt_covariates(option(WINSORIZED), AVAILABLE) == ["winsorized_session_seconds"]


def test_assigned_columns_that_exist_are_the_covariates() -> None:
    spec = make_spec("ols", outcome="converted", exposure="variant", covariates_from_ctx=True)
    assigned = option("Set ctx['covariates'] = ['platform', 'session_seconds']; fit OLS.")
    found = with_assigned_covariates(spec, assigned, AVAILABLE)
    assert found.covariates == ["platform", "session_seconds"]
    assert not found.covariates_from_ctx


def test_a_spec_that_reads_ctx_is_left_alone() -> None:
    spec = make_spec("ols", outcome="converted", exposure="variant", covariates_from_ctx=True)
    reads = option("Regress converted on variant and ctx['covariates'] with OLS.")
    assert unbuilt_covariates(reads, AVAILABLE) == []
    assert with_assigned_covariates(spec, reads, AVAILABLE) == spec
