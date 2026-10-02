from __future__ import annotations

import itertools
import json
import random
from pathlib import Path
from typing import Any

from borges.analysis.models import AnalysisPlan


def load_events(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def seeded_plan(events: list[dict[str, Any]]) -> AnalysisPlan:
    """The first recorded plan whose options all carry code and none comes from the adversary."""
    for event in events:
        if event.get("type") != "plan.ready":
            continue
        plan = AnalysisPlan.model_validate(event["data"]["plan"])
        options = [o for step in plan.steps for o in step.options]
        if all(o.code for o in options) and all(o.origin != "adversary" for o in options):
            return plan
    raise ValueError("the recording has no coded plan.ready without adversary options")


def grid_size(plan: AnalysisPlan) -> int:
    size = 1
    for step in plan.steps:
        size *= len(step.options)
    return size


def enumerate_grid(plan: AnalysisPlan) -> list[dict[str, str]]:
    """The full Cartesian product of the options of every step, defaults first in each step."""
    per_step: list[list[str]] = []
    for step in plan.steps:
        ids = [step.default.id] + [o.id for o in step.options if o.id != step.default.id]
        per_step.append(ids)
    step_ids = [s.id for s in plan.steps]
    return [dict(zip(step_ids, combo, strict=True)) for combo in itertools.product(*per_step)]


def sample_grid(
    universes: list[dict[str, str]], plan: AnalysisPlan, cap: int | None, seed: int
) -> list[dict[str, str]]:
    """All universes when they fit under the cap; otherwise the baseline plus a uniform sample."""
    if cap is None or len(universes) <= cap:
        return list(universes)
    baseline = plan.default_choices()
    others = [u for u in universes if u != baseline]
    rng = random.Random(seed)
    picked = rng.sample(others, cap - 1)
    return [baseline, *picked]
