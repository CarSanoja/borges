from __future__ import annotations

from borges.analysis.code_guard_missing import missing_violations

DROP = "Drop missing. Drop rows where any of ['job', 'education'] is NA. Return filtered DataFrame."
INDICATOR = (
    "Missing indicator. For each column create a missing indicator and impute with 'missing'."
)
FILLED = """
def apply(df, ctx):
    df = df.copy()
    df["job_missing"] = df["job"].isna().astype(int)
    df["job"] = df["job"].fillna("missing")
    return df
"""
DROPPED = """
def apply(df, ctx):
    return df.dropna(subset=["job", "education"])
"""
MASKED = """
def apply(df, ctx):
    return df[df["job"].notna() & df["education"].notna()]
"""


def test_a_drop_option_coded_as_a_fill_is_refused() -> None:
    [problem] = missing_violations(FILLED, DROP)
    assert "fills them instead" in problem


def test_a_fill_option_coded_as_a_drop_is_refused() -> None:
    [problem] = missing_violations(DROPPED, INDICATOR)
    assert "removes rows instead" in problem


def test_faithful_code_passes() -> None:
    assert missing_violations(DROPPED, DROP) == []
    assert missing_violations(MASKED, DROP) == []
    assert missing_violations(FILLED, INDICATOR) == []


def test_specs_that_mention_both_or_neither_are_left_alone() -> None:
    both = "Drop rows with missing outcome; impute missing covariates with the median."
    assert missing_violations(FILLED, both) == []
    assert missing_violations(FILLED, "Winsorize balance at the 1st and 99th percentiles.") == []


def test_a_treatment_indicator_is_not_a_missing_value_indicator() -> None:
    spec = "Create a treatment indicator and drop rows with a missing outcome."
    assert missing_violations(DROPPED, spec) == []
