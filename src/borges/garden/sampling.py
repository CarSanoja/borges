from __future__ import annotations

import itertools
import json
import random
import zlib
from typing import Literal

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden, NoopOption
from borges.garden.noop import noop_pairs

SAMPLE_DRAWS = 30
MIN_SAMPLE = 5
SAMPLE_SEED = 20261003
SampleKind = Literal["grid", "sample"]


def grid_options(plan: AnalysisPlan, noops: list[NoopOption]) -> dict[str, list[str]]:
    skipped = noop_pairs(noops)
    return {
        step.id: [o.id for o in step.options if (step.id, o.id) not in skipped]
        for step in plan.decision_steps
    }


def seed_for(plan: AnalysisPlan, noops: list[NoopOption]) -> int:
    """The seed comes from the plan's grid, so the same plan draws the same sample on any machine
    and a rerun of a case quotes the same share; it is shown in the note so the draw can be
    repeated. A seed from the run id drew another sample on every run of a scripted case."""
    options = grid_options(plan, noops)
    specs = {
        step.id: [[o.id, o.spec] for o in step.options if o.id in options[step.id]]
        for step in plan.decision_steps
    }
    return zlib.crc32(json.dumps(specs, sort_keys=True).encode())


def full_grid(plan: AnalysisPlan, noops: list[NoopOption]) -> list[dict[str, str]]:
    options = grid_options(plan, noops)
    base = plan.default_choices()
    steps = list(options)
    return [
        {**base, **dict(zip(steps, combo, strict=True))}
        for combo in itertools.product(*(options[s] for s in steps))
    ]


def draw_grid(
    plan: AnalysisPlan,
    noops: list[NoopOption],
    draws: int = SAMPLE_DRAWS,
    seed: int = SAMPLE_SEED,
) -> list[dict[str, str]]:
    """Independent uniform draws from the grid: every decision picks each of its options equally."""
    rng = random.Random(seed)
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


def grid_draws(
    plan: AnalysisPlan, noops: list[NoopOption], garden: Garden, budget: int, seed: int
) -> tuple[list[dict[str, str]], list[dict[str, str]], SampleKind]:
    """The whole grid when its unexplored cells fit the budget, otherwise a uniform sample.

    A grid of 72 cells was summarised by 12 draws (10 distinct results), a share with an interval
    of about 40 to 90 per cent; when the budget covers every cell the share is exact. A prefix of
    the enumeration is never used, since it would favour the options listed first.
    """
    grid = full_grid(plan, noops)
    explored = {choice_key(u.choices) for u in garden.universes.values()}
    unexplored = [c for c in grid if choice_key(c) not in explored]
    if len(unexplored) <= budget:
        return grid, unexplored, "grid"
    kept, new = affordable_prefix(draw_grid(plan, noops, seed=seed), garden, budget)
    return kept, new, "sample"
