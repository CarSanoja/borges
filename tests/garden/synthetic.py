from __future__ import annotations

from borges.analysis.models import (
    AnalysisPlan,
    AnalysisResult,
    ColumnProfile,
    DatasetProfile,
    DecisionRule,
    Option,
    Step,
    StepTrace,
)
from borges.garden.executor_ids import universe_id
from borges.garden.models import Garden, Universe

RULE = DecisionRule(metric="diff", threshold=0.0)


def option(
    oid: str, default: bool = False, code: str | None = None, label: str | None = None
) -> Option:
    return Option(
        id=oid,
        label=label or f"label {oid}",
        rationale=f"why {oid}",
        spec=f"spec {oid}",
        is_default=default,
        code=code,
    )


def plan_of(*steps: Step, notes: dict[str, str] | None = None) -> AnalysisPlan:
    columns = [
        ColumnProfile(name=name, dtype="int", n_missing=0, n_unique=2, note=note)
        for name, note in (notes or {}).items()
    ]
    return AnalysisPlan(
        question="q",
        estimand="e",
        decision_rule=RULE,
        dataset=DatasetProfile(name="d", n_rows=100, columns=columns),
        steps=list(steps),
    )


def step_of(step_id: str, kind: str, *options: Option) -> Step:
    return Step(
        id=step_id, title=f"Step {step_id}", kind=kind, description="", options=list(options)
    )


def result(estimate: float, half: float = 0.2, p: float = 0.01, n: int = 100) -> AnalysisResult:
    return AnalysisResult(
        estimate=estimate, ci_low=estimate - half, ci_high=estimate + half, p_value=p, n=n
    )


def trace(step_id: str, rows_after: int = 100, fingerprint: str | None = None, **design: object):
    return StepTrace(
        step_id=step_id,
        option_id="x",
        rows_before=100,
        rows_after=rows_after,
        fingerprint=fingerprint,
        design=dict(design) or None,
    )


def universe(
    plan: AnalysisPlan,
    changes: dict[str, str],
    res: AnalysisResult,
    kind: str | None = None,
    traces: list[StepTrace] | None = None,
) -> Universe:
    choices = {**plan.default_choices(), **changes}
    baseline = not changes
    verdict = plan.decision_rule.label(res)
    return Universe(
        id=universe_id(choices),
        choices=choices,
        changed=[s.id for s in plan.steps if choices[s.id] != s.default.id],
        kind=kind or ("baseline" if baseline else "single" if len(changes) == 1 else "combination"),
        status="done",
        result=res,
        verdict=verdict,
        flipped=False if baseline else None,
        traces=traces or [],
    )


def garden_of(plan: AnalysisPlan, *universes: Universe) -> Garden:
    garden = Garden()
    base = next(u for u in universes if u.kind == "baseline")
    garden.baseline_id = base.id
    for item in universes:
        item.flipped = item.kind != "baseline" and item.verdict != base.verdict
        garden.add(item)
    return garden
