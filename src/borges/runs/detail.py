from __future__ import annotations

from borges.garden.models import Universe
from borges.runs.models import RunSnapshot, UniverseDetail, UniverseStepDetail
from borges.runs.reproduce_commands import ReproducibleUniverse, with_reproduce


def _checkpoint_id(universe: Universe, index: int, n_steps: int) -> str | None:
    offset = 1 if len(universe.checkpoints) > n_steps else 0
    position = index + offset
    return universe.checkpoints[position] if position < len(universe.checkpoints) else None


def build_universe_detail(
    snapshot: RunSnapshot, universe_id: str, recorded_case: str | None = None
) -> ReproducibleUniverse:
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
    detail = UniverseDetail(universe=universe, steps=steps, reproduce_command="")
    return with_reproduce(detail, snapshot.run_id, recorded_case)
