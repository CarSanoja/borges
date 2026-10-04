from __future__ import annotations

from borges.analysis.code_guard_wide import wide_columns, wide_dummy_violations
from borges.analysis.models import ColumnProfile, DatasetProfile

WIDE = {"refNum": 3147}


def test_a_formula_that_dummy_codes_a_wide_column_is_refused() -> None:
    code = "def estimate(df, ctx):\n    f = 'y ~ x + C(refNum) + C(league)'\n    return f\n"
    [problem] = wide_dummy_violations(code, WIDE)
    assert "'refNum' has 3147 distinct values" in problem and "cluster" in problem


def test_get_dummies_on_a_wide_column_is_refused() -> None:
    code = "def estimate(df, ctx):\n    return pd.get_dummies(df, columns=['refNum'])\n"
    assert wide_dummy_violations(code, WIDE)


def test_clustering_on_a_wide_column_is_allowed() -> None:
    code = (
        "def estimate(df, ctx):\n"
        "    groups = pd.factorize(df['refNum'])[0]\n"
        "    return pd.get_dummies(df['league'])\n"
    )
    assert wide_dummy_violations(code, WIDE) == []


def test_wide_columns_come_from_the_profile() -> None:
    columns = [
        ColumnProfile(name="refNum", dtype="int64", n_missing=0, n_unique=3147, summary={}),
        ColumnProfile(name="league", dtype="str", n_missing=0, n_unique=4, summary={}),
    ]
    assert wide_columns(DatasetProfile(name="d", n_rows=146028, columns=columns)) == {
        "refNum": 3147
    }
    assert wide_columns(DatasetProfile(name="d", n_rows=10000, columns=columns)) == {}
