from __future__ import annotations

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.analysis.planner_trend import date_text_columns, numeric_trend
from borges.analysis.schemas import PlannedOption, PlannedStep

PROFILE = DatasetProfile(
    name="triage",
    n_rows=4000,
    columns=[
        ColumnProfile(name="arrival_month", dtype="object", n_missing=0, n_unique=12),
        ColumnProfile(name="site", dtype="object", n_missing=0, n_unique=3),
        ColumnProfile(name="week", dtype="int64", n_missing=0, n_unique=52),
    ],
    sample_rows=[
        {"arrival_month": "2025-11", "site": "South", "week": 3},
        {"arrival_month": "2025-01", "site": "North", "week": 40},
    ],
)


def trend_step(spec: str, label: str = "Add linear time trend") -> PlannedStep:
    options = [
        PlannedOption(id="trend", label=label, rationale="r", spec=spec, is_default=True),
        PlannedOption(id="none", label="No time trend", rationale="r", spec="Leave ctx unchanged."),
    ]
    return PlannedStep(id="t", title="Time trend", kind="feature", description="d", options=options)


def test_months_written_as_text_are_the_dated_columns() -> None:
    assert date_text_columns(PROFILE) == ["arrival_month"]


def test_a_trend_on_months_written_as_text_is_entered_as_a_number() -> None:
    [step] = numeric_trend([trend_step("Append 'arrival_month' to ctx['covariates'].")], PROFILE)
    spec = step.options[0].spec
    assert "write arrival_month_months = (year * 12 + month)" in spec
    assert "put 'arrival_month_months' in ctx['covariates'] in place of 'arrival_month'" in spec
    assert step.options[1].spec == "Leave ctx unchanged."


def test_other_options_and_numeric_columns_are_left_as_planned() -> None:
    adjust = trend_step("Append 'arrival_month' to ctx['covariates'].", label="Month dummies")
    numeric = trend_step("Append 'week' to ctx['covariates'] as a linear trend.")
    built = trend_step(
        "Add arrival_month_months, the months since arrival_month began, as a trend."
    )
    for planned in (adjust, numeric, built):
        assert numeric_trend([planned], PROFILE) == [planned]
