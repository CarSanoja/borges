from __future__ import annotations

import asyncio
import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pandas as pd

from borges.analysis.coder import code_plan
from borges.analysis.models import AnalysisPlan
from borges.analysis.narrator import narrate
from borges.analysis.planner import plan_analysis
from borges.analysis.profile import profile_dataframe
from borges.config import Settings
from borges.garden.executor import GardenExecutor
from borges.garden.influence import build_report
from borges.garden.models import Flip, Garden, Report
from borges.garden.search import combination_flip_choices, minimal_flip, single_flip_choices
from borges.garden.verify import verify_flip
from borges.llm.client import BudgetExceeded, LLMClient, UsageTotals
from borges.runs.adversary_round import run_adversary_round
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionCodedData
from borges.runs.inputs import ResolvedRun
from borges.runs.runner import UniverseRunner, publish_plan
from borges.sandbox.backend import BranchBackend

MAX_COMBINATIONS_PER_LEVEL = 10


def load_dataframe(data: bytes) -> pd.DataFrame:
    try:
        return pd.read_parquet(io.BytesIO(data))
    except Exception as exc:
        raise ValueError(f"the dataset is not a readable parquet file: {exc}") from exc


class Pipeline:
    """The whole analysis of ARCHITECTURE.md section 3, emitting the events of section 5."""

    def __init__(
        self,
        settings: Settings,
        llm: LLMClient,
        backend: BranchBackend,
        emitter: RunEmitter,
        resolved: ResolvedRun,
    ) -> None:
        self.settings = settings
        self.llm = llm
        self.backend = backend
        self.emitter = emitter
        self.resolved = resolved
        self.garden = Garden()
        self.executor: GardenExecutor | None = None
        self.flip: Flip | None = None
        self.report: Report | None = None
        emitter.usage_probe = self._usage

    def _usage(self) -> tuple[UsageTotals, int]:
        created = self.executor.checkpoints_created if self.executor else 0
        return self.llm.totals, created

    @asynccontextmanager
    async def _stage(self, name: str, detail: str = "") -> AsyncIterator[None]:
        await self.emitter.stage(name, "started", detail)
        yield
        await self.emitter.stage(name, "done")
        await self.emitter.usage()

    async def _plan(self) -> AnalysisPlan:
        resolved = self.resolved
        async with self._stage("profiling"):
            frame = load_dataframe(resolved.data)
            profile = await asyncio.to_thread(profile_dataframe, frame, resolved.dataset_name)
        async with self._stage("planning"):
            plan = await plan_analysis(self.llm, profile, resolved.question, resolved.decision_rule)
            await publish_plan(self.emitter, plan)

        async def on_coded(
            step_id: str, option_id: str, ok: bool, attempts: int, error: str | None
        ) -> None:
            payload = OptionCodedData(
                step_id=step_id, option_id=option_id, ok=ok, attempts=attempts, error=error
            )
            await self.emitter.emit("option.coded", payload.model_dump(mode="json"))

        async with self._stage("coding"):
            plan = await code_plan(self.llm, plan, on_coded, self.settings.borges_concurrency)
            await publish_plan(self.emitter, plan)
        return plan

    async def _search(self, plan: AnalysisPlan) -> None:
        executor = GardenExecutor(
            self.backend,
            plan,
            self.resolved.data,
            self.emitter.emit,
            self.settings.borges_concurrency,
        )
        self.executor = executor
        await executor.setup()
        runner = UniverseRunner(
            self.llm, plan, executor, self.garden, self.emitter, self.resolved.max_universes
        )
        async with self._stage("baseline"):
            baseline = await runner.run(plan.default_choices(), "baseline")
            if baseline.status != "done":
                raise RuntimeError(f"the baseline analysis failed: {baseline.error}")
        async with self._stage("single_flips"):
            await runner.run_many(single_flip_choices(plan), "single")
        if runner.remaining > 0:
            async with self._stage("adversary"):
                await run_adversary_round(self.llm, plan, runner, self.emitter, baseline)
        self.flip = minimal_flip(plan, self.garden)
        if self.flip is None and runner.remaining > 0:
            await self._combinations(plan, runner)

    async def _combinations(self, plan: AnalysisPlan, runner: UniverseRunner) -> None:
        async with self._stage("combination_flips"):
            for size in range(2, len(plan.decision_steps) + 1):
                if self.flip is not None or runner.remaining <= 0:
                    break
                limit = min(MAX_COMBINATIONS_PER_LEVEL, runner.remaining)
                choices = combination_flip_choices(plan, self.garden, size, limit)
                if not choices:
                    break
                await self.emitter.stage("combination_flips", "started", f"{size} changes")
                await runner.run_many(choices, "combination")
                self.flip = minimal_flip(plan, self.garden)

    async def _verify(self, plan: AnalysisPlan) -> None:
        if self.flip is None:
            return
        await self.emitter.emit("flip.found", {"flip": self.flip.model_dump(mode="json")})
        async with self._stage("verifying"):
            self.flip = await verify_flip(
                self.backend, plan, self.resolved.data, self.flip, self.garden
            )
            await self.emitter.emit("flip.verified", {"flip": self.flip.model_dump(mode="json")})

    async def _narrate(self, plan: AnalysisPlan, report: Report) -> None:
        async with self._stage("narrating"):
            try:
                narrative, caveats = await narrate(self.llm, plan, report)
                report.narrative, report.caveats = narrative, caveats
            except BudgetExceeded:
                raise
            except Exception as exc:
                report.caveats = [*report.caveats, f"Narrative unavailable: {exc}"]
            await self.emitter.emit("report.ready", {"report": report.model_dump(mode="json")})

    async def run(self) -> Report:
        plan = await self._plan()
        await self._search(plan)
        await self._verify(plan)
        self.report = build_report(plan, self.garden, self.flip)
        await self._narrate(plan, self.report)
        return self.report
