from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.analysis.code_guard import check_code

ROOT = Path(__file__).resolve().parents[2]
MESSAGE = (
    "a model step may only drop incomplete rows; this filters rows by value, which is a "
    "decision that belongs to a filter step: remove it"
)


def model(body: str) -> str:
    lines = "\n".join(f"    {line}" for line in body.strip().splitlines())
    return (
        "import pandas as pd\nimport numpy as np\nimport statsmodels.api as sm\n\n\n"
        f"def estimate(df, ctx):\n{lines}\n"
    )


def row_errors(body: str) -> list[str]:
    return [v for v in check_code(model(body), "model") if "row filter" in v]


@pytest.mark.parametrize(
    "body",
    [
        "df = df[df['attention_check'] == 1].copy()\nreturn {}",
        "d = df.loc[df['g'] == 'a']\nreturn {}",
        "d = df.loc[df['g'].isin(['a', 'b']), :]\nreturn {}",
        "d = df.query('g == 1')\nreturn {}",
        "d = df[(df['x'] > 0) & (df['y'] < 3)]\nreturn {}",
        "d = df[df['x'].between(1, 3)]\nreturn {}",
        "mask = df['x'] > 0\nd = df[mask]\nreturn {}",
        "d = df[~df['g'].isin(['a'])]\nreturn {}",
        "d = df[df['x'].notna() & (df['x'] > 0)]\nreturn {}",
    ],
)
def test_value_row_filters_are_rejected_and_quoted(body: str) -> None:
    errors = row_errors(body)
    assert errors and all(MESSAGE in e for e in errors)
    assert "row filter `" in errors[0]


def test_error_quotes_the_offending_expression() -> None:
    [error] = row_errors("df = df[df['attention_check'] == 1].copy()\nreturn {}")
    assert "df[df['attention_check'] == 1]" in error
    assert error.startswith("line ")


@pytest.mark.parametrize(
    "body",
    [
        "d = df[['a', 'b']]\nreturn {}",
        "cols = ['a', 'b']\nX = df[cols]\nreturn {}",
        "X = df[cols]\nreturn {}",
        "d = df.dropna(subset=['a'])\nreturn {}",
        "d = df[df['a'].notna()]\nreturn {}",
        "d = df[~df['a'].isna()]\nreturn {}",
        "d = df[df[['a', 'b']].notnull().all(axis=1)]\nreturn {}",
        "mask = df['a'].notna() & df['b'].notna()\nd = df[mask]\nreturn {}",
        "d = pd.get_dummies(df, columns=['g'], drop_first=True)\nreturn {}",
        "res = sm.OLS(df['y'], df[['x']]).fit()\nb = res.params['x']\nreturn {}",
        "res = sm.OLS(df['y'], df[['x']]).fit()\nsmall = res.params[res.pvalues < 0.05]\nreturn {}",
        "ci = res.conf_int().loc['x']\nreturn {}",
        "df['z'] = df['x'] * 2\nreturn {}",
        "df.loc[df['x'] > 0, 'z'] = 1\nreturn {}",
        "p = np.array([1.0, 2.0])\np[p < 1.5] = 0\nreturn {}",
        "t = df.loc[df['variant'] == 'treatment', 'converted']\nreturn {}",
        "t = df[df['variant'] == 'control']['converted']\nreturn {}",
    ],
)
def test_legitimate_model_code_is_accepted(body: str) -> None:
    assert row_errors(body) == []


def test_rule_applies_to_model_steps_only() -> None:
    code = "def apply(df, ctx):\n    return df[df['x'] > 0].copy()\n"
    assert check_code(code, "filter") == []


def test_real_code_from_the_failed_marp_run_is_rejected() -> None:
    path = (
        ROOT / "runs/r_20261002T133635_b00f08/fixtures/coder__step_model_interaction.model_ols.json"
    )
    if not path.exists():
        pytest.skip("run directory is not part of the checkout")
    code = json.loads(path.read_text())["parsed"]["code"]
    errors = [v for v in check_code(code, "model") if "row filter" in v]
    assert len(errors) == 1 and "df[df['attention_check'] == 1]" in errors[0]


def test_every_scripted_model_code_is_accepted() -> None:
    codes = []
    for path in (ROOT / "cases").glob("*/fixtures/coder__*.json"):
        code = json.loads(path.read_text()).get("parsed", {}).get("code", "")
        if "def estimate" in code:
            codes.append((path.name, code))
    assert len(codes) >= 10
    for name, code in codes:
        assert [v for v in check_code(code, "model") if "row filter" in v] == [], name
