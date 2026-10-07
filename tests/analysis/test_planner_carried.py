from __future__ import annotations

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.analysis.planner_carried import carry_computed
from borges.analysis.schemas import PlannedOption, PlannedStep

PROFILE = DatasetProfile(
    name="vote",
    n_rows=502,
    columns=[
        ColumnProfile(name=n, dtype="float64", n_missing=0, n_unique=10)
        for n in ("WorkerID", "DateTesting", "Relationship", "Vote")
    ],
)


def step(sid: str, kind: str, spec: str, produces: list[str] | None = None) -> PlannedStep:
    options = [
        PlannedOption(id="a", label="a", rationale="r", spec=spec, is_default=True),
        PlannedOption(id="b", label="b", rationale="r", spec=spec + " (other)"),
    ]
    return PlannedStep(
        id=sid, title=sid, kind=kind, description="d", options=options, produces=produces or []
    )


RUN_35 = [
    step(
        "filter_days",
        "filter",
        "df = df.copy(); cycle_day = 28 - days_to_next_onset; for WorkerID 15 and 16 set "
        "cycle_day to 11 and 18; keep rows where cycle_day is 7-14 or 17-25",
    ),
    step("committed", "feature", "committed = Relationship in [3, 4]", ["committed"]),
    step("fertility", "feature", "high_fertile = 1 where cycle_day is 7-14", ["high_fertile"]),
    step("model", "model", "Vote ~ high_fertile * committed; alpha = 0.05"),
]


def test_a_value_a_filter_computes_and_a_later_step_reads_is_passed_on() -> None:
    """fertility_vote on 7 October, runs 34 and 35: the later steps read cycle_day, which the
    filter computed and never declared, so their coders were told it did not exist."""
    out = carry_computed(RUN_35, PROFILE)
    assert out[0].produces == ["cycle_day"]
    assert [s.produces for s in out[1:]] == [["committed"], ["high_fertile"], []]


def test_names_that_are_not_read_later_or_are_computed_again_are_left_alone() -> None:
    steps = [
        step("t", "filter", "tmp = Vote * 2; keep rows where tmp > 1"),
        step("f", "feature", "tmp = Relationship; flag = tmp > 2", ["flag"]),
        step("m", "model", "Vote ~ flag"),
    ]
    assert [s.produces for s in carry_computed(steps, PROFILE)] == [[], ["flag"], []]


def test_a_feature_step_s_notation_is_left_as_planned() -> None:
    """The recorded hurricanes plan: 'fem = masfem' in a feature step whose code writes fem_x."""
    steps = [
        step("femininity", "feature", "fem = masfem."),
        step("interaction", "feature", "Include fem*dam."),
        step("m", "model", "NB2 GLM"),
    ]
    assert [s.produces for s in carry_computed(steps, PROFILE)] == [[], [], []]


def test_a_name_the_data_already_has_is_not_carried() -> None:
    steps = [
        step("t", "filter", "Vote = Vote.astype(int); keep rows where Vote > 0"),
        step("m", "model", "Vote ~ 1"),
    ]
    assert carry_computed(steps, PROFILE)[0].produces == []
