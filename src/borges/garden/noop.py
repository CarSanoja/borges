from __future__ import annotations

from borges.analysis.models import AnalysisPlan
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


def _counterparts_agree(plan: AnalysisPlan, garden: Garden, step_id: str, option_id: str) -> bool:
    default = plan.step(step_id).default.id
    for universe in garden.finished():
        if universe.kind == "verification" or universe.choices.get(step_id) != option_id:
            continue
        if len(universe.changed) < 2 or universe.result is None:
            continue
        twin = garden.universes.get(universe_id({**universe.choices, step_id: default}))
        if twin is None or twin.result is None:
            continue
        if result_key(twin.result) != result_key(universe.result):
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
            same_result = result_key(single.result) == result_key(baseline.result)
            if not (same_data or same_result):
                continue
            if not same_data and not _counterparts_agree(plan, garden, step.id, option.id):
                continue
            reason = FINGERPRINT_REASON if same_data else RESULT_REASON
            found.append(
                NoopOption(step_id=step.id, option_id=option.id, label=option.label, reason=reason)
            )
    return found


def noop_pairs(noops: list[NoopOption]) -> set[tuple[str, str]]:
    return {(n.step_id, n.option_id) for n in noops}


def has_noop(universe: Universe, pairs: set[tuple[str, str]]) -> bool:
    return any((step_id, universe.choices[step_id]) in pairs for step_id in universe.changed)
