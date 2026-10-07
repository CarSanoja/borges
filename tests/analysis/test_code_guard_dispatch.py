from __future__ import annotations

import pytest

from borges.analysis.code_guard import check_code

REFUSED = [
    ("import numpy as np\n    np.test()", "attribute 'test'"),
    ("import pandas as pd\n    pd.test()", "attribute 'test'"),
    ("import statsmodels.api as sm\n    sm.test()", "attribute 'test'"),
    ("import pandas as pd\n    pd.show_versions()", "attribute 'show_versions'"),
    ("df.groupby('a').agg({'b': 'to_pickle'})", "'to_pickle' passed to .agg()"),
    ("df.pipe('to_csv')", "'to_csv' passed to .pipe()"),
    ("df.apply('to_json')", "'to_json' passed to .apply()"),
    ("df.transform(['mean', 'to_clipboard'])", "'to_clipboard' passed to .transform()"),
]
ALLOWED = [
    "df = df.groupby('a').agg({'b': 'mean', 'c': ['sum', 'count']}).reset_index()",
    "df['x'] = df['x'].map({1: 'single', 3: 'committed'})",
    "df['z'] = df['x'].transform('to_numeric') if False else df['x']",
]


def wrap(body: str) -> str:
    return f"def apply(df, ctx):\n    {body}\n    return df\n"


@pytest.mark.parametrize(("body", "expected"), REFUSED)
def test_a_method_reached_by_attribute_or_by_name_is_refused(body: str, expected: str) -> None:
    assert any(expected in v for v in check_code(wrap(body), "transform"))


@pytest.mark.parametrize("body", ALLOWED)
def test_statistics_and_labels_named_by_string_pass(body: str) -> None:
    assert check_code(wrap(body), "transform") == []
