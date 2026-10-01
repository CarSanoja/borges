from __future__ import annotations

from collections.abc import Sequence

from borges.analysis.coder import repair_option
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.garden.executor import GardenExecutor
from borges.garden.models import Garden, Universe, UniverseKind
from borges.llm.client import BudgetExceeded, LLMClient
from borges.llm.gather import gather_cancelling
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionCodedData


async def publish_plan(emitter: RunEmitter, plan: AnalysisPlan) -> None:
    await emitter.emit("plan.ready", {"plan": plan.model_dump(mode="json")})


class UniverseRunner:
    """Runs universes through the executor, repairs a failing option once, tracks the budget."""

    def __init__(
        self,
        llm: LLMClient,
        plan: AnalysisPlan,
        executor: GardenExecutor,
        garden: Garden,
        emitter: RunEmitter,
        max_universes: int,
    ) -> None:
        self.llm = llm
        self.plan = plan
        self.executor = executor
        self.garden = garden
        self.emitter = emitter
        self.max_universes = max_universes

    @property
    def remaining(self) -> int:
        return max(0, self.max_universes - len(self.garden.universes))

    def _repair_target(self, universe: Universe, kind: UniverseKind) -> tuple[Step, Option] | None:
        steps = self.plan.steps
        failing = len(universe.checkpoints)
        if failing >= len(steps):
            return None
        for step in [steps[failing], *reversed(steps[:failing])]:
            option = step.option(universe.choices[step.id])
            if kind == "baseline" or not option.is_default:
                return step, option
        return None

    async def _repair(self, universe: Universe, kind: UniverseKind) -> dict[str, str] | None:
        target = self._repair_target(universe, kind)
        if target is None:
            return None
        step, option = target
        try:
            repaired = await repair_option(
                self.llm, self.plan, step, option, universe.error or "unknown error"
            )
        except BudgetExceeded:
            raise
        except Exception:
            return None
        index = next(i for i, o in enumerate(step.options) if o.id == option.id)
        step.options[index] = repaired
        coded = OptionCodedData(
            step_id=step.id, option_id=repaired.id, ok=repaired.code is not None, attempts=2
        )
        await self.emitter.emit("option.coded", coded.model_dump(mode="json"))
        await publish_plan(self.emitter, self.plan)
        return {**universe.choices, step.id: repaired.id}

    async def run(self, choices: dict[str, str], kind: UniverseKind) -> Universe:
        universe = await self.executor.run_universe(choices, kind)
        if universe.status == "failed":
            repaired = await self._repair(universe, kind)
            if repaired is not None:
                universe = await self.executor.run_universe(repaired, kind)
        self.garden.add(universe)
        if kind == "baseline":
            self.garden.baseline_id = universe.id
        return universe

    async def run_many(
        self, choice_list: Sequence[dict[str, str]], kind: UniverseKind
    ) -> list[Universe]:
        selected = list(choice_list)[: self.remaining]
        return list(await gather_cancelling(self.run(c, kind) for c in selected))
