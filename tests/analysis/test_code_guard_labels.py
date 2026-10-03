from __future__ import annotations

import pytest

from borges.analysis.code_guard import check_code


def model_code(body: str) -> str:
    return (
        "import statsmodels.formula.api as smf\nimport pandas as pd\n\n\n"
        f"def estimate(df, ctx):\n{body}\n"
    )


@pytest.mark.parametrize(
    "label",
    [
        "C(variant)[T.treatment]",
        "treatment[T.True]",
        "C(age_band)[T.18-24]",
        "C(a)[T.x]:C(b)[T.y]",
        "np.log(z)",
    ],
)
def test_accept_coefficient_labels(label: str) -> None:
    body = f'    model = smf.ols("y ~ x", df).fit()\n    return model.params["{label}"]'
    assert check_code(model_code(body), "model") == []


@pytest.mark.parametrize(
    "formula",
    [
        "converted ~ C(variant)[T.treatment]",
        "y ~ C(g)[T.a] + z",
    ],
)
def test_reject_indexed_terms_in_formulas_with_a_hint(formula: str) -> None:
    body = f'    return smf.ols("{formula}", df).fit()'
    problems = check_code(model_code(body), "model")
    assert any("params['C(x)[T.level]']" in p for p in problems)


@pytest.mark.parametrize(
    "label",
    [
        "C(g)[T.open(x)]",
        "C(g)[T.a][T.b](x)",
        "x[pd.io.common.os.getcwd()]",
        "C(g)[__class__]",
    ],
)
def test_reject_labels_that_hide_calls(label: str) -> None:
    body = f'    model = smf.ols("y ~ x", df).fit()\n    return model.params["{label}"]'
    assert check_code(model_code(body), "model")
