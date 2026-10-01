from __future__ import annotations

from itertools import combinations

from borges.analysis.models import AnalysisPlan, AnalysisResult, Comparator
from borges.garden.executor import universe_id
from borges.garden.models import Change, Flip, Garden, Universe

UNKNOWN_DEFENSIBILITY = 0.9
Z_95 = 1.96


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


def single_flip_choices(plan: AnalysisPlan) -> list[dict[str, str]]:
    base = plan.default_choices()
    return [
        {**base, step.id: option.id}
        for step in plan.decision_steps
        for option in step.options
        if option.id != step.default.id
    ]


def _z(plan: AnalysisPlan, result: AnalysisResult) -> float:
    se = max((result.ci_high - result.ci_low) / (2 * Z_95), 1e-12)
    z = (result.estimate - plan.decision_rule.threshold) / se
    return z if plan.decision_rule.comparator is Comparator.GT else -z


def _movement(plan: AnalysisPlan, baseline: Universe, universe: Universe) -> float:
    assert baseline.result is not None and universe.result is not None
    delta = _z(plan, universe.result) - _z(plan, baseline.result)
    return -delta if plan.decision_rule.is_positive(baseline.result) else delta


def pair_flip_choices(plan: AnalysisPlan, garden: Garden, limit: int) -> list[dict[str, str]]:
    baseline = garden.baseline
    if baseline is None or baseline.result is None or limit <= 0:
        return []
    scored: list[tuple[float, str, str]] = []
    for universe in garden.finished():
        if len(universe.changed) != 1:
            continue
        step_id = universe.changed[0]
        scored.append((_movement(plan, baseline, universe), step_id, universe.choices[step_id]))
    scored.sort(key=lambda item: -item[0])
    base = plan.default_choices()
    pairs: list[tuple[float, dict[str, str]]] = []
    for (score_a, step_a, opt_a), (score_b, step_b, opt_b) in combinations(scored, 2):
        if step_a == step_b:
            continue
        choices = {**base, step_a: opt_a, step_b: opt_b}
        if universe_id(choices) in garden.universes:
            continue
        pairs.append((score_a + score_b, choices))
    pairs.sort(key=lambda item: -item[0])
    return [choices for _, choices in pairs[:limit]]


def minimal_flip(plan: AnalysisPlan, garden: Garden) -> Flip | None:
    baseline = garden.baseline
    if baseline is None or baseline.result is None or baseline.verdict is None:
        return None
    candidates: list[tuple[tuple[int, float, float], Universe, list[Change]]] = []
    for universe in garden.finished():
        if universe.flipped is not True or universe.verdict is None or universe.result is None:
            continue
        changes = changes_for(plan, universe.choices)
        defensibility = (
            min(
                (UNKNOWN_DEFENSIBILITY if c.defensibility is None else c.defensibility)
                for c in changes
            )
            if changes
            else UNKNOWN_DEFENSIBILITY
        )
        move = abs(universe.result.estimate - baseline.result.estimate)
        candidates.append(((len(changes), -defensibility, -move), universe, changes))
    if not candidates:
        return None
    _, best, changes = min(candidates, key=lambda item: item[0])
    assert best.result is not None and best.verdict is not None
    return Flip(
        universe_id=best.id,
        changes=changes,
        baseline_result=baseline.result,
        flipped_result=best.result,
        baseline_verdict=baseline.verdict,
        flipped_verdict=best.verdict,
    )
