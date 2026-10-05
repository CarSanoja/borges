"""Options that do not change the analysis.

At 5061161 a checkout plan offered "Keep binary 0/1 outcome" next to the default "Convert to
percentage points", both writing conv_pp. The model step's code had been repaired to divide its
coefficient by 100 (Borges converts proportions to percentage points itself), so under the binary
option every universe reported the default's estimate and interval divided by 100 with the same
p-value and n, and the summary said the option "shrinks the estimate to -0.0013". Among 10,518
pairs of recorded universes with equal n, those 12 were the only results a factor of 100 apart
with equal p-values. Such an option changes the unit, not the analysis, and is treated as a no-op.
"""

from __future__ import annotations

import math

from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.garden.executor_ids import universe_id
from borges.garden.models import Garden, NoopOption, Universe
from borges.garden.result_key import result_key

FINGERPRINT_REASON = (
    "its step output is identical to the baseline option's (same data fingerprint after "
    "the step), so it is not a different analysis"
)
RESULT_REASON = (
    "it gives the same result as the baseline in every universe it appears in (estimate, "
    "confidence interval and n equal to 6 significant digits), so it is not a different analysis"
)
UNIT_REASON = (
    "in every universe it appears in it gives the baseline's estimate and interval {how} by 100, "
    "with the same p-value and n: it changes the unit of the outcome, not the analysis"
)
UNIT_FACTORS = (100.0, 0.01)
SCALED = ("estimate", "ci_low", "ci_high")


def unit_factor(result: AnalysisResult, reference: AnalysisResult) -> float | None:
    """The factor that turns `result` into `reference` when they differ at most by a unit."""
    if result_key(result) == result_key(reference):
        return 1.0
    if not math.isclose(result.p_value, reference.p_value, rel_tol=1e-6, abs_tol=1e-12):
        return None
    for factor in UNIT_FACTORS:
        scaled = result.model_copy(update={k: getattr(result, k) * factor for k in SCALED})
        if result_key(scaled) == result_key(reference):
            return factor
    return None


def _reason(factor: float) -> str:
    if factor == 1.0:
        return RESULT_REASON
    return UNIT_REASON.format(how="divided" if factor > 1 else "multiplied")


def single_universe(garden: Garden, step_id: str, option_id: str) -> Universe | None:
    return next(
        (
            u
            for u in garden.finished()
            if u.kind != "verification"
            and u.changed == [step_id]
            and u.choices[step_id] == option_id
        ),
        None,
    )


def trace_of(universe: Universe, step_id: str):
    return next((t for t in universe.traces if t.step_id == step_id), None)


def _same_data(baseline: Universe, single: Universe, step_id: str) -> bool:
    before, after = trace_of(baseline, step_id), trace_of(single, step_id)
    return (
        before is not None
        and after is not None
        and before.fingerprint is not None
        and before.fingerprint == after.fingerprint
    )


def _counterparts_agree(
    plan: AnalysisPlan, garden: Garden, step_id: str, option_id: str, factor: float = 1.0
) -> bool:
    default = plan.step(step_id).default.id
    for universe in garden.finished():
        if universe.kind == "verification" or universe.choices.get(step_id) != option_id:
            continue
        if len(universe.changed) < 2 or universe.result is None:
            continue
        twin = garden.universes.get(universe_id({**universe.choices, step_id: default}))
        if twin is None or twin.result is None:
            continue
        if unit_factor(universe.result, twin.result) != factor:
            return False
    return True


def noop_options(plan: AnalysisPlan, garden: Garden) -> list[NoopOption]:
    baseline = garden.baseline
    if baseline is None or baseline.result is None:
        return []
    found: list[NoopOption] = []
    for step in plan.decision_steps:
        for option in step.options:
            if option.id == step.default.id:
                continue
            single = single_universe(garden, step.id, option.id)
            if single is None or single.result is None:
                continue
            same_data = _same_data(baseline, single, step.id)
            factor = unit_factor(single.result, baseline.result)
            if not same_data and factor is None:
                continue
            if not same_data and not _counterparts_agree(
                plan, garden, step.id, option.id, factor or 1.0
            ):
                continue
            reason = FINGERPRINT_REASON if same_data else _reason(factor or 1.0)
            found.append(
                NoopOption(step_id=step.id, option_id=option.id, label=option.label, reason=reason)
            )
    return found


def noop_pairs(noops: list[NoopOption]) -> set[tuple[str, str]]:
    return {(n.step_id, n.option_id) for n in noops}


def has_noop(universe: Universe, pairs: set[tuple[str, str]]) -> bool:
    return any((step_id, universe.choices[step_id]) in pairs for step_id in universe.changed)
