from __future__ import annotations

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


def combination_flip_choices(
    plan: AnalysisPlan, garden: Garden, size: int, limit: int
) -> list[dict[str, str]]:
    """Beam step: extend each finished universe of size - 1 changes by one more single change.

    Candidates are ranked by the measured movement of the parent plus the measured movement of
    the added single change, so the search spends sandboxes where the verdict is closest to
    flipping.
    """
    baseline = garden.baseline
    if baseline is None or baseline.result is None or limit <= 0 or size < 2:
        return []
    finished = [u for u in garden.finished() if u.kind != "verification"]
    singles = [
        (_movement(plan, baseline, u), u.changed[0], u.choices[u.changed[0]])
        for u in finished
        if len(u.changed) == 1
    ]
    parents = [u for u in finished if len(u.changed) == size - 1]
    best: dict[str, tuple[float, dict[str, str]]] = {}
    for parent in parents:
        parent_move = _movement(plan, baseline, parent)
        for move, step_id, option_id in singles:
            if step_id in parent.changed:
                continue
            choices = {**parent.choices, step_id: option_id}
            uid = universe_id(choices)
            if uid in garden.universes:
                continue
            score = parent_move + move
            if uid not in best or score > best[uid][0]:
                best[uid] = (score, choices)
    ranked = sorted(best.values(), key=lambda item: -item[0])
    return [choices for _, choices in ranked[:limit]]


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
