from __future__ import annotations

import pytest

from borges.analysis.harness import parse_error, parse_output
from tests.analysis.test_harness import make_step, run, workdir  # noqa: F401

HEAD = "import numpy as np\nimport pandas as pd\nimport statsmodels.api as sm\n\n"


def outcome(workdir, body: str):  # noqa: F811
    code = HEAD + "def estimate(df, ctx):\n" + body
    step, option = make_step("s1", "model", code)
    proc = run(workdir, step, option)
    return parse_error(proc.stdout), parse_output(proc.stdout)[1]


def test_tuple_of_five_is_normalised(workdir) -> None:  # noqa: F811
    error, result = outcome(workdir, "    return (0.5, 0.2, 0.8, 0.04, 10)\n")
    assert error is None and result is not None
    assert (result.estimate, result.ci_low, result.ci_high, result.n) == (0.5, 0.2, 0.8, 10)


def test_tuple_with_interval_pair_is_normalised(workdir) -> None:  # noqa: F811
    error, result = outcome(workdir, "    return [0.5, (0.2, 0.8), 0.04, 10]\n")
    assert error is None and result is not None and result.ci_high == 0.8


def test_numpy_and_series_values_in_a_dict_are_normalised(workdir) -> None:  # noqa: F811
    body = (
        "    return {'estimate': np.float64(0.5), 'ci_low': np.array([0.2]),\n"
        "            'ci_high': pd.Series([0.8]), 'p_value': np.float32(0.04), 'n': np.int64(10)}\n"
    )
    error, result = outcome(workdir, body)
    assert error is None and result is not None
    assert result.estimate == 0.5 and result.n == 10


def test_statsmodels_results_with_one_term_is_normalised(workdir) -> None:  # noqa: F811
    body = (
        "    X = sm.add_constant(df[['age']])\n    return sm.OLS(df['y'].astype(float), X).fit()\n"
    )
    error, result = outcome(workdir, body)
    assert error is None and result is not None
    assert result.ci_low < result.estimate < result.ci_high and result.n == 10


def test_statsmodels_results_with_many_terms_gets_a_clear_error(workdir) -> None:  # noqa: F811
    body = (
        "    X = sm.add_constant(df[['age', 'y']])\n"
        "    return sm.OLS(df['age'].astype(float), X).fit()\n"
    )
    error, result = outcome(workdir, body)
    assert result is None
    assert "2 non-intercept terms" in (error or "") and "for the one term" in (error or "")


def test_bare_float_gets_a_clear_error(workdir) -> None:  # noqa: F811
    error, result = outcome(workdir, "    return 0.5\n")
    assert result is None and "bare number" in (error or "")


def test_unknown_shape_gets_a_clear_error(workdir) -> None:  # noqa: F811
    error, result = outcome(workdir, "    return None\n")
    assert result is None and "not a NoneType" in (error or "")


@pytest.mark.parametrize("body", ["    return (1, 2, 3)\n"])
def test_short_sequence_gets_a_clear_error(workdir, body: str) -> None:  # noqa: F811
    error, result = outcome(workdir, body)
    assert result is None and "sequence of 3 items" in (error or "")
