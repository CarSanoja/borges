from __future__ import annotations

import math

from borges.analysis.models import AnalysisPlan, AnalysisResult, Option
from borges.garden.models import DuplicateOption, Garden, NoopOption
from borges.garden.noop import noop_options, single_universe

REL_TOL = 1e-9
ABS_TOL = 1e-12

DUPLICATE_REASON = (
    "its single-change universe gives the same estimate, confidence interval, p-value and n "
    "as '{kept}' of the same step (equal within 1e-9 relative), so it is not an independent path"
)


def same_result(a: AnalysisResult, b: AnalysisResult) -> bool:
    values = ((a.estimate, b.estimate), (a.ci_low, b.ci_low), (a.ci_high, b.ci_high))
    return (
        a.n == b.n
        and all(math.isclose(x, y, rel_tol=REL_TOL, abs_tol=ABS_TOL) for x, y in values)
        and math.isclose(a.p_value, b.p_value, rel_tol=REL_TOL, abs_tol=ABS_TOL)
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
        candidates: list[tuple[tuple[bool, int], Option, AnalysisResult]] = []
        for position, option in enumerate(step.options):
            if option.id == step.default.id or (step.id, option.id) in skipped:
                continue
            single = single_universe(garden, step.id, option.id)
            if single is not None and single.result is not None:
                candidates.append((_rank(option, position), option, single.result))
        candidates.sort(key=lambda item: item[0])
        kept: list[tuple[Option, AnalysisResult]] = []
        for _, option, outcome in candidates:
            twin = next((k for k, r in kept if same_result(r, outcome)), None)
            if twin is None:
                kept.append((option, outcome))
                continue
            found.append(
                DuplicateOption(
                    step_id=step.id,
                    option_id=option.id,
                    label=option.label,
                    reason=DUPLICATE_REASON.format(kept=twin.label),
                    kept_option_id=twin.id,
                    kept_label=twin.label,
                    kept_origin=twin.origin,
                )
            )
    return found


def excluded_options(plan: AnalysisPlan, garden: Garden) -> list[NoopOption]:
    noops = noop_options(plan, garden)
    return [*noops, *duplicate_options(plan, garden, noops)]
