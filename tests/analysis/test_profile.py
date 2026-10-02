from __future__ import annotations

import json

import numpy as np
import pandas as pd

from borges.analysis.profile import profile_dataframe


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "x": [1.0, 2.0, 3.0, np.nan],
            "flag": [True, False, True, True],
            "cat": ["a", "b", "a", None],
            "n": np.array([1, 2, 3, 4], dtype=np.int64),
        }
    )


def test_profile_columns_and_counts() -> None:
    profile = profile_dataframe(_frame(), "demo")
    assert profile.name == "demo"
    assert profile.n_rows == 4
    by_name = {c.name: c for c in profile.columns}
    assert by_name["x"].n_missing == 1
    assert by_name["x"].n_unique == 3
    assert by_name["cat"].n_missing == 1


def test_numeric_summary() -> None:
    summary = {c.name: c for c in profile_dataframe(_frame(), "d").columns}["x"].summary
    assert summary == {"mean": 2.0, "std": 1.0, "min": 1.0, "p50": 2.0, "max": 3.0}


def test_bool_summary() -> None:
    summary = {c.name: c for c in profile_dataframe(_frame(), "d").columns}["flag"].summary
    assert summary == {"share_true": 0.75}


def test_categorical_summary_top_values() -> None:
    summary = {c.name: c for c in profile_dataframe(_frame(), "d").columns}["cat"].summary
    assert summary["top_1"] == "a: 2"
    assert summary["top_2"] == "b: 1"


def test_categorical_limited_to_five() -> None:
    df = pd.DataFrame({"c": list("abcdefgh")})
    summary = profile_dataframe(df, "d").columns[0].summary
    assert len(summary) == 5


def test_sample_rows_json_safe() -> None:
    profile = profile_dataframe(_frame(), "d", sample=3)
    assert len(profile.sample_rows) == 3
    text = json.dumps(profile.sample_rows, allow_nan=False)
    assert "NaN" not in text
    assert profile.sample_rows[0]["n"] == 1
    assert isinstance(profile.sample_rows[0]["n"], int)


def test_empty_numeric_column() -> None:
    df = pd.DataFrame({"x": [np.nan, np.nan]})
    assert profile_dataframe(df, "d").columns[0].summary == {}


def test_profile_serialises() -> None:
    profile = profile_dataframe(_frame(), "d")
    assert profile.model_dump_json()


def test_flagged_columns_by_name_and_outlier() -> None:
    from borges.analysis.profile_flags import describe_inclusion_candidates, flagged_columns

    df = pd.DataFrame(
        {
            "isBot": [True] + [False] * 59,
            "spend": [float(i % 7) for i in range(59)] + [50000.0],
            "score": list(range(60)),
        }
    )
    flags, outliers = flagged_columns(profile_dataframe(df, "d"))
    assert [c.name for c in flags] == ["isBot"]
    assert [c.name for c in outliers] == ["spend"]
    text = describe_inclusion_candidates(profile_dataframe(df, "d"))
    assert "isBot" in text and "spend" in text and "score" not in text
