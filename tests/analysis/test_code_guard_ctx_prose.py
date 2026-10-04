from __future__ import annotations

import pytest

from borges.analysis.code_guard_ctx import ctx_writes, varying_ctx_keys
from tests.analysis.test_code_guard_ctx import MODEL, plan, step


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("Write 'wb_overall_mean' to ctx['outcome']. Return df.", {"outcome": "'wb_overall_mean'"}),
        ("Store ['age', 'gender'] in ctx['covariates'].", {"covariates": "['age', 'gender']"}),
        ('Set ctx["outcome"] to "wb_psych_mean" and return.', {"outcome": '"wb_psych_mean"'}),
        ("ctx['outcome'] = 'wb_soc_mean'", {"outcome": "'wb_soc_mean'"}),
        ("Write the standardised score to ctx['religiosity'].", {}),
    ],
)
def test_a_spec_states_a_ctx_write_in_code_or_in_prose(spec: str, expected: dict) -> None:
    assert ctx_writes(spec) == expected


def test_an_outcome_chosen_in_prose_is_a_key_the_model_must_read() -> None:
    outcome = step(
        "wb",
        "Select well-being outcome",
        "feature",
        "Use the pre-existing wb_overall_mean column. Write 'wb_overall_mean' to ctx['outcome'].",
        "Use the pre-existing wb_psych_mean column. Write 'wb_psych_mean' to ctx['outcome'].",
    )
    assert varying_ctx_keys(plan(outcome, MODEL), MODEL) == {"outcome": "Select well-being outcome"}


def test_a_cluster_column_or_none_chosen_by_an_earlier_step_must_be_read() -> None:
    adjust = step(
        "adj",
        "Adjust",
        "feature",
        "ctx['covariates'] = []\nctx['cluster_col'] = None",
        "ctx['covariates'] = []\nctx['cluster_col'] = 'group'",
    )
    found = varying_ctx_keys(plan(adjust, MODEL), MODEL)
    assert found == {"cluster_col": "Adjust"}
