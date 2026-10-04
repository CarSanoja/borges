from __future__ import annotations

from borges.analysis.code_guard_complete import complete_case_violations
from borges.analysis.models import ColumnProfile, DatasetProfile

FIT = (
    "import statsmodels.api as sm\n\n\n"
    "def estimate(df, ctx):\n"
    "{prep}"
    "    X = sm.add_constant(data[['masfem'] + ctx['covariates']])\n"
    "    fit = sm.OLS(data['y'], X{kw}).fit()\n"
    "    return float(fit.params['masfem'])\n"
)


def profile(missing: int) -> DatasetProfile:
    columns = [
        ColumnProfile(name="y", dtype="float64", n_missing=0, n_unique=90),
        ColumnProfile(name="ndam", dtype="float64", n_missing=missing, n_unique=90),
    ]
    return DatasetProfile(name="d", n_rows=93, columns=columns)


def test_a_model_that_never_drops_incomplete_rows_is_refused_when_data_have_gaps() -> None:
    code = FIT.format(prep="    data = df\n", kw="")
    [problem] = complete_case_violations(code, profile(2))
    assert "missing values (ndam)" in problem and "df.dropna(subset=[...])" in problem


def test_complete_cases_by_dropna_mask_or_missing_drop_pass() -> None:
    for prep, kw in [
        ("    data = df.dropna(subset=['y', 'masfem'] + ctx['covariates'])\n", ""),
        ("    data = df[df[['y', 'masfem']].notna().all(axis=1)]\n", ""),
        ("    data = df\n", ", missing='drop'"),
    ]:
        assert complete_case_violations(FIT.format(prep=prep, kw=kw), profile(2)) == []


def test_data_without_gaps_need_no_complete_case_step() -> None:
    assert complete_case_violations(FIT.format(prep="    data = df\n", kw=""), profile(0)) == []


def test_the_formula_api_drops_incomplete_rows_itself() -> None:
    code = (
        "import statsmodels.formula.api as smf\n\n\n"
        "def estimate(df, ctx):\n"
        "    return float(smf.ols('y ~ masfem + ndam', data=df).fit().params['masfem'])\n"
    )
    assert complete_case_violations(code, profile(2)) == []
