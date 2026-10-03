from __future__ import annotations

import random

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden, NoopOption
from borges.garden.noop import noop_pairs

SAMPLE_DRAWS = 12
MIN_SAMPLE = 5
SAMPLE_SEED = 20261003


def grid_options(plan: AnalysisPlan, noops: list[NoopOption]) -> dict[str, list[str]]:
    skipped = noop_pairs(noops)
    return {
        step.id: [o.id for o in step.options if (step.id, o.id) not in skipped]
        for step in plan.decision_steps
    }


def draw_grid(
    plan: AnalysisPlan, noops: list[NoopOption], draws: int = SAMPLE_DRAWS
) -> list[dict[str, str]]:
    """Independent uniform draws from the grid: every decision picks each of its options equally."""
    rng = random.Random(SAMPLE_SEED)
    options = grid_options(plan, noops)
    base = plan.default_choices()
    return [
        {**base, **{sid: rng.choice(ids) for sid, ids in options.items()}} for _ in range(draws)
    ]


def choice_key(choices: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(choices.items()))


def sampled_ids(garden: Garden, kept: list[dict[str, str]]) -> list[str]:
    by_choices = {choice_key(u.choices): u.id for u in garden.universes.values()}
    return [by_choices[key] for key in map(choice_key, kept) if key in by_choices]


def affordable_prefix(
    draws: list[dict[str, str]], garden: Garden, budget: int
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """The longest prefix of the draws whose unexplored universes fit the budget.

    Cutting the sequence at the first draw that does not fit keeps the kept draws a plain
    random sample; dropping only the expensive ones would favour the beam-explored universes.
    """
    explored = {choice_key(u.choices) for u in garden.universes.values()}
    kept: list[dict[str, str]] = []
    new: dict[tuple[tuple[str, str], ...], dict[str, str]] = {}
    for choices in draws:
        key = choice_key(choices)
        fresh = key not in explored and key not in new
        if fresh and len(new) >= budget:
            break
        if fresh:
            new[key] = choices
        kept.append(choices)
    return kept, list(new.values())
