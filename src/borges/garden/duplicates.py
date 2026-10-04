from __future__ import annotations

import math

from borges.analysis.models import AnalysisPlan, AnalysisResult, Option
from borges.garden.models import DuplicateOption, Garden, NoopOption, Universe
from borges.garden.noop import noop_options, single_universe

REL_TOL = 1e-9
ABS_TOL = 1e-12

DUPLICATE_REASON = (
    "its single-change universe gives the same estimate, confidence interval, p-value and n "
    "as '{kept}' of the same step (equal within 1e-9 relative), so it is not an independent path"
)


SAME_ESTIMATE_REASON = (
    "its single-change universe gives the same point estimate and n as '{kept}' of the same step "
    "(equal within 1e-9 relative) and the same verdict; only the interval and p-value differ, so "
    "it is the same finding with a different standard error, not an independent path"
)


def _close(x: float, y: float) -> bool:
    return math.isclose(x, y, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def same_result(a: AnalysisResult, b: AnalysisResult) -> bool:
    values = ((a.estimate, b.estimate), (a.ci_low, b.ci_low), (a.ci_high, b.ci_high))
    return a.n == b.n and all(_close(x, y) for x, y in values) and _close(a.p_value, b.p_value)


def same_finding(a: Universe, b: Universe) -> bool:
    if a.result is None or b.result is None:
        return False
    if same_result(a.result, b.result):
        return True
    return (
        a.verdict is not None
        and a.verdict == b.verdict
        and a.result.n == b.result.n
        and _close(a.result.estimate, b.result.estimate)
    )


def _rank(option: Option, position: int) -> tuple[bool, int]:
    return (option.origin == "adversary", position)


def duplicate_options(
    plan: AnalysisPlan, garden: Garden, noops: list[NoopOption] | None = None
) -> list[DuplicateOption]:
    noops = noop_options(plan, garden) if noops is None else noops
    skipped = {(n.step_id, n.option_id) for n in noops}
    found: list[DuplicateOption] = []
    for step in plan.decision_steps:
        candidates: list[tuple[tuple[bool, int], Option, Universe]] = []
        for position, option in enumerate(step.options):
            if option.id == step.default.id or (step.id, option.id) in skipped:
                continue
            single = single_universe(garden, step.id, option.id)
            if single is not None and single.result is not None:
                candidates.append((_rank(option, position), option, single))
        candidates.sort(key=lambda item: item[0])
        kept: list[tuple[Option, Universe]] = []
        for _, option, outcome in candidates:
            twin, twin_universe = next(
                ((k, r) for k, r in kept if same_finding(r, outcome)), (None, None)
            )
            if twin is None:
                kept.append((option, outcome))
                continue
            found.append(
                DuplicateOption(
                    step_id=step.id,
                    option_id=option.id,
                    label=option.label,
                    reason=_reason(twin, twin_universe, outcome),
                    kept_option_id=twin.id,
                    kept_label=twin.label,
                    kept_origin=twin.origin,
                )
            )
    return found


def _reason(twin: Option, twin_universe: Universe, outcome: Universe) -> str:
    identical = twin_universe.result is not None and outcome.result is not None
    exact = identical and same_result(twin_universe.result, outcome.result)
    template = DUPLICATE_REASON if exact else SAME_ESTIMATE_REASON
    return template.format(kept=twin.label)


def excluded_options(plan: AnalysisPlan, garden: Garden) -> list[NoopOption]:
    noops = noop_options(plan, garden)
    return [*noops, *duplicate_options(plan, garden, noops)]
