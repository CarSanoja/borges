from __future__ import annotations

from borges.analysis.models import AnalysisPlan, AnalysisResult, Comparator
from borges.garden.executor_ids import universe_id
from borges.garden.flips import (
    UNKNOWN_DEFENSIBILITY,
    beyond_threshold,
    changes_for,
    flip_kind,
    ranked_flips,
)
from borges.garden.models import Flip, Garden, Universe
from borges.garden.noop import noop_options, noop_pairs

Z_95 = 1.96

__all__ = [
    "UNKNOWN_DEFENSIBILITY",
    "beyond_threshold",
    "changes_for",
    "combination_flip_choices",
    "contaminated_flip",
    "flip_kind",
    "minimal_flip",
    "single_flip_choices",
]


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
    skipped = noop_pairs(noop_options(plan, garden))
    singles = [
        (_movement(plan, baseline, u), u.changed[0], u.choices[u.changed[0]])
        for u in finished
        if len(u.changed) == 1 and (u.changed[0], u.choices[u.changed[0]]) not in skipped
    ]
    parents = [
        u
        for u in finished
        if len(u.changed) == size - 1 and not any((s, u.choices[s]) in skipped for s in u.changed)
    ]
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
    return next((f for f in ranked_flips(plan, garden) if not f.contaminated), None)


def contaminated_flip(plan: AnalysisPlan, garden: Garden) -> Flip | None:
    return next((f for f in ranked_flips(plan, garden) if f.contaminated), None)
