from __future__ import annotations

from typing import Literal

from borges.analysis.models import AnalysisPlan, AnalysisResult, Comparator, DecisionRule
from borges.garden.contamination import contamination_reason
from borges.garden.estimand import estimand_detail
from borges.garden.models import Change, Flip, Garden, Universe
from borges.garden.noop import has_noop, noop_options, noop_pairs

UNKNOWN_DEFENSIBILITY = 0.9


def beyond_threshold(rule: DecisionRule, result: AnalysisResult) -> bool:
    if rule.comparator is Comparator.GT:
        return result.estimate > rule.threshold
    return result.estimate < rule.threshold


def flip_kind(
    rule: DecisionRule, baseline: AnalysisResult, flipped: AnalysisResult
) -> Literal["direction", "significance"]:
    if beyond_threshold(rule, baseline) != beyond_threshold(rule, flipped):
        return "direction"
    return "significance"


def _build(plan: AnalysisPlan, garden: Garden, universe: Universe, changes: list[Change]) -> Flip:
    baseline = garden.baseline
    assert baseline is not None and baseline.result is not None and baseline.verdict is not None
    assert universe.result is not None and universe.verdict is not None
    reason = contamination_reason(plan, garden, changes, universe.id)
    return Flip(
        universe_id=universe.id,
        changes=changes,
        baseline_result=baseline.result,
        flipped_result=universe.result,
        baseline_verdict=baseline.verdict,
        flipped_verdict=universe.verdict,
        kind=flip_kind(plan.decision_rule, baseline.result, universe.result),
        estimand_change=estimand_detail(baseline, universe),
        contaminated=reason is not None,
        contamination_reason=reason,
    )


def changes_for(plan: AnalysisPlan, choices: dict[str, str]) -> list[Change]:
    changes: list[Change] = []
    for step in plan.steps:
        chosen = choices.get(step.id, step.default.id)
        if chosen == step.default.id:
            continue
        option = step.option(chosen)
        changes.append(
            Change(
                step_id=step.id,
                step_title=step.title,
                from_option=step.default.id,
                to_option=option.id,
                to_label=option.label,
                rationale=option.rationale,
                source=option.source,
                defensibility=option.defensibility,
            )
        )
    return changes


def _weakest(changes: list[Change]) -> float:
    return min(
        (UNKNOWN_DEFENSIBILITY if c.defensibility is None else c.defensibility for c in changes),
        default=UNKNOWN_DEFENSIBILITY,
    )


def ranked_flips(plan: AnalysisPlan, garden: Garden) -> list[Flip]:
    baseline = garden.baseline
    if baseline is None or baseline.result is None or baseline.verdict is None:
        return []
    pairs = noop_pairs(noop_options(plan, garden))
    scored: list[tuple[tuple[bool, bool, int, float, float], Flip]] = []
    for universe in garden.finished():
        if universe.flipped is not True or universe.verdict is None or universe.result is None:
            continue
        if has_noop(universe, pairs):
            continue
        changes = changes_for(plan, universe.choices)
        flip = _build(plan, garden, universe, changes)
        move = abs(universe.result.estimate - baseline.result.estimate)
        key = (
            flip.contaminated,
            flip.estimand_change is not None,
            len(changes),
            -_weakest(changes),
            -move,
        )
        scored.append((key, flip))
    return [flip for _, flip in sorted(scored, key=lambda item: item[0])]
