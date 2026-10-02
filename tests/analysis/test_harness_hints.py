from __future__ import annotations

from pathlib import Path

import pytest

from tests.analysis.test_harness_effects import DROPS_COLUMN, make, run

DISTRIBUTION_HINT = (
    "statsmodels has no probability distributions here: read p-values from the fitted result "
    "(result.pvalues) and intervals from result.conf_int(); if you really need a distribution "
    "use scipy.stats.norm"
)
COVARIATE_HINT = (
    "to choose which covariates a later model uses, keep every column and store the list of "
    "names in ctx (for example ctx['covariates'] = [...]); the model step reads that list"
)


def _uses(attribute: str, module: str = "statsmodels.api") -> str:
    return (
        f"import {module} as sm\n\n"
        "def estimate(df, ctx):\n"
        f"    p = sm.{attribute}.cdf(1.0)\n"
        '    return {"estimate": 0.0, "ci_low": -1.0, "ci_high": 1.0, "p_value": p, "n": 1}\n'
    )


@pytest.mark.parametrize("attribute", ["norm", "t", "chi2", "f"])
def test_statsmodels_distribution_attribute_gets_the_hint(tmp_path: Path, attribute: str) -> None:
    done, error, _ = run(tmp_path, *make("model", _uses(attribute)))
    assert done.returncode == 1
    assert error is not None and f"has no attribute '{attribute}'" in error
    assert DISTRIBUTION_HINT in error


def test_statsmodels_submodule_gets_the_hint(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("model", _uses("norm", "statsmodels.formula.api")))
    assert error is not None and DISTRIBUTION_HINT in error


def test_unrelated_attribute_error_gets_no_hint(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("model", _uses("bogus")))
    assert error is not None and "distributions" not in error


def test_dropped_columns_error_explains_covariate_choice(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", DROPS_COLUMN))
    assert error is not None and COVARIATE_HINT in error
