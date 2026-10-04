from __future__ import annotations

from borges.analysis.covariate_ids import covariate_id_violations, identifier_columns
from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.analysis.planner_validation import plan_shortfalls
from borges.analysis.schemas import PlannedOption, PlannedStep


def column(name: str, dtype: str, unique: int) -> ColumnProfile:
    return ColumnProfile(name=name, dtype=dtype, n_missing=0, n_unique=unique)


PROFILE = DatasetProfile(
    name="redcard",
    n_rows=146028,
    columns=[
        column("playerShort", "object", 1585),
        column("refNum", "int64", 3147),
        column("games", "int64", 47),
        column("height", "float64", 60),
        column("country", "object", 24),
        column("monkey", "int64", 300),
        column("user_id", "int64", 51),
        column("comment", "object", 900),
    ],
)


def test_identifiers_are_id_named_or_text_with_very_many_levels() -> None:
    assert identifier_columns(PROFILE) == {
        "playerShort": 1585,
        "refNum": 3147,
        "user_id": 51,
        "comment": 900,
    }


def test_a_covariate_list_with_identifiers_is_refused() -> None:
    code = "def apply(df, ctx):\n    ctx['covariates'] = ['playerShort', 'refNum', 'games']\n"
    found = covariate_id_violations(code, PROFILE)
    assert len(found) == 2
    assert found[0].startswith("ctx['covariates'] lists 'playerShort', an identifier with 1585")
    assert covariate_id_violations("ctx['covariates'] = ['games', 'country']", PROFILE) == []


def test_the_planner_is_asked_to_drop_identifiers_from_covariate_lists() -> None:
    def option(i: str, spec: str, default: bool = False) -> PlannedOption:
        return PlannedOption(id=i, label=i, rationale="r", spec=spec, is_default=default)

    step = PlannedStep(
        id="cov",
        title="Covariates",
        kind="feature",
        description="",
        produces=["covariates"],
        options=[
            option("none", "Set ctx['covariates'] = []", True),
            option("min", "Set ctx['covariates'] = ['playerShort', 'refNum', 'games']"),
        ],
    )
    problems = plan_shortfalls([step], PROFILE)
    listed = [p for p in problems if p.startswith("These identifier columns")]
    assert listed and "playerShort, refNum." in listed[0]
