from __future__ import annotations

from borges.garden.executor import GardenExecutor, universe_id
from borges.garden.models import Universe, UniverseKind
from borges.telemetry.scopes import universe_span


async def run_universe_traced(
    executor: GardenExecutor, choices: dict[str, str], kind: UniverseKind
) -> Universe:
    plan = getattr(executor, "plan", None)
    full = {**plan.default_choices(), **choices} if plan is not None else choices
    with universe_span(universe_id(full), kind) as span:
        universe = await executor.run_universe(choices, kind)
        span.set_attribute("borges.universe.status", universe.status)
        span.set_attribute("borges.universe.flipped", bool(universe.flipped))
        span.set_attribute("borges.universe.checkpoints", len(universe.checkpoints))
        if universe.verdict:
            span.set_attribute("borges.universe.verdict", universe.verdict)
        return universe
