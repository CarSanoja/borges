from __future__ import annotations

from collections.abc import Sequence

from borges.analysis.coder import repair_option
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.garden.executor import GardenExecutor, universe_id
from borges.garden.executor_errors import sandbox_failed
from borges.garden.models import Garden, Universe, UniverseKind
from borges.llm.client import BudgetExceeded, LLMClient
from borges.llm.gather import gather_cancelling
from borges.runs.adversary_review import review_verdict
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionCodedData
from borges.runs.universe_tracing import run_universe_traced
from borges.runtime.context import RunContext
from borges.runtime.universe_checkpoint import RestoredUniverses, universe_key, universe_payload


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
        context: RunContext | None = None,
        restored: RestoredUniverses | None = None,
        root_id: str | None = None,
    ) -> None:
        self.llm = llm
        self.plan = plan
        self.executor = executor
        self.garden = garden
        self.emitter = emitter
        self.max_universes = max_universes
        self.context = context
        self.restored = restored
        self.root_id = root_id
        self.running: list[dict[str, str]] = []

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

    def _in_use(self, step_id: str, option_id: str, mine: dict[str, str]) -> bool:
        done = any(
            u.status == "done" and u.choices.get(step_id) == option_id
            for u in self.garden.universes.values()
        )
        others = [c for c in self.running if c is not mine]
        return done or any(c.get(step_id) == option_id for c in others)

    async def _swap(self, step: Step, option: Option) -> None:
        index = next(i for i, o in enumerate(step.options) if o.id == option.id)
        step.options[index] = option
        coded = OptionCodedData(
            step_id=step.id, option_id=option.id, ok=option.code is not None, attempts=2
        )
        await self.emitter.emit("option.coded", coded.model_dump(mode="json"))
        await publish_plan(self.emitter, self.plan)

    async def _repair(
        self, universe: Universe, kind: UniverseKind, mine: dict[str, str]
    ) -> tuple[dict[str, str], Step, Option] | None:
        """Repair the option at fault once, unless other universes already ran its code."""
        target = self._repair_target(universe, kind)
        if target is None:
            return None
        step, option = target
        if self._in_use(step.id, option.id, mine):
            return None
        try:
            repaired = await repair_option(
                self.llm, self.plan, step, option, universe.error or "unknown error"
            )
        except BudgetExceeded:
            raise
        except Exception:
            return None
        if repaired.code == option.code or not await self._faithful(step, repaired):
            return None
        await self._swap(step, repaired)
        return {**universe.choices, step.id: repaired.id}, step, option

    async def _faithful(self, step: Step, option: Option) -> bool:
        """A repair answers a failure further down the universe, so it can bend the option to fit.

        At d29a189 the bank repair of an option whose spec said "Do not create missing indicator
        columns" created them so that a later covariate step found its columns, and the option
        became a no-op. The repaired code is reviewed against its spec before it replaces the old.
        """
        key = f"reviewer:repair:{step.id}:{option.id}"
        verdict = await review_verdict(self.llm, self.plan, self.emitter, step, option, key)
        return verdict is None or (verdict.faithful and not verdict.changes_estimand)

    def _restore(self, universe_id: str) -> Universe:
        assert self.restored is not None
        universe = self.restored.universe(universe_id)
        self.garden.add(universe)
        if universe.kind == "baseline":
            self.garden.baseline_id = universe.id
        self.emitter.universes_finished += 1
        return universe

    def _record(self, universe: Universe) -> None:
        if self.context is None:
            return
        payload = universe_payload(universe, self.plan, self.root_id)
        self.context.save(universe_key(universe.id), self.emitter.seq, payload)

    async def run(self, choices: dict[str, str], kind: UniverseKind) -> Universe:
        if self.context is not None:
            self.context.check()
        full = {**self.plan.default_choices(), **choices}
        if self.restored and universe_id(full) in self.restored.ids:
            return self._restore(universe_id(full))
        self.running.append(full)
        try:
            universe = await run_universe_traced(self.executor, choices, kind)
            if universe.status == "failed" and sandbox_failed(universe.error):
                universe = await run_universe_traced(self.executor, choices, kind)
            if universe.status == "failed" and not sandbox_failed(universe.error):
                repaired = await self._repair(universe, kind, full)
                if repaired is not None:
                    retried = await run_universe_traced(self.executor, repaired[0], kind)
                    if retried.status == "failed":
                        await self._swap(repaired[1], repaired[2])
                    else:
                        universe = retried
        finally:
            self.running.remove(full)
        self.garden.add(universe)
        if kind == "baseline":
            self.garden.baseline_id = universe.id
        self._record(universe)
        return universe

    async def run_many(
        self, choice_list: Sequence[dict[str, str]], kind: UniverseKind
    ) -> list[Universe]:
        selected = list(choice_list)[: self.remaining]
        return list(await gather_cancelling(self.run(c, kind) for c in selected))
