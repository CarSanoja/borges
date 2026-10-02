from __future__ import annotations

from borges.analysis.models import (
    AnalysisPlan,
    ColumnProfile,
    DatasetProfile,
    DecisionRule,
    Option,
    Step,
)


def option(option_id: str, label: str = "", spec: str = "", default: bool = False) -> Option:
    return Option(
        id=option_id,
        label=label or f"label {option_id}",
        rationale="why",
        spec=spec or f"spec {option_id}",
        is_default=default,
    )


def profile(note: str | None = None, rows: int = 100) -> DatasetProfile:
    return DatasetProfile(
        name="d",
        n_rows=rows,
        columns=[
            ColumnProfile(name="amount", dtype="float64", n_missing=0, n_unique=9, note=note),
            ColumnProfile(name="group", dtype="object", n_missing=1, n_unique=2),
        ],
    )


def plan(data: DatasetProfile | None = None) -> AnalysisPlan:
    return AnalysisPlan(
        question="does it ship?",
        estimand="mean diff",
        decision_rule=DecisionRule(metric="diff"),
        dataset=data or profile(),
        steps=[
            Step(
                id="s1",
                title="Filter",
                kind="filter",
                description="",
                options=[option("a", default=True), option("b", "Drop outliers", "drop top 1%")],
            ),
            Step(
                id="s2",
                title="Model",
                kind="model",
                description="",
                options=[option("x", default=True), option("y")],
            ),
        ],
    )
