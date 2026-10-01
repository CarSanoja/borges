from __future__ import annotations

import shlex

from borges.analysis import harness
from borges.analysis.models import AnalysisPlan
from borges.garden.models import Universe
from borges.runs.models import RunSnapshot, UniverseDetail, UniverseStepDetail


def _chain_command(plan: AnalysisPlan, universe: Universe) -> str:
    commands = [
        shlex.join(harness.step_command(step.id, universe.choices[step.id])) for step in plan.steps
    ]
    return " && ".join(commands)


def _checkpoint_id(universe: Universe, index: int, n_steps: int) -> str | None:
    offset = 1 if len(universe.checkpoints) > n_steps else 0
    position = index + offset
    return universe.checkpoints[position] if position < len(universe.checkpoints) else None


def build_universe_detail(snapshot: RunSnapshot, universe_id: str) -> UniverseDetail:
    """Raises KeyError when the run has no plan yet or the universe is unknown."""
    universe = snapshot.garden.universes[universe_id]
    plan = snapshot.plan
    if plan is None:
        raise KeyError(universe_id)
    traces = {t.step_id: t for t in universe.traces}
    steps = [
        UniverseStepDetail(
            step=step,
            option=step.option(universe.choices.get(step.id, step.default.id)),
            trace=traces.get(step.id),
            changed=universe.choices.get(step.id, step.default.id) != step.default.id,
            checkpoint_id=_checkpoint_id(universe, index, len(plan.steps)),
        )
        for index, step in enumerate(plan.steps)
    ]
    flip = snapshot.flip
    verified = flip is not None and flip.universe_id == universe_id and flip.reproduce_command
    command = flip.reproduce_command if verified and flip else _chain_command(plan, universe)
    return UniverseDetail(universe=universe, steps=steps, reproduce_command=command or "")
