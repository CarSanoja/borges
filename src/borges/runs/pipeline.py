from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager

from borges.analysis.coder import code_plan
from borges.analysis.coder_smoke import SmokeConfig
from borges.analysis.models import AnalysisPlan, CodingSummary
from borges.analysis.planner import plan_analysis
from borges.analysis.profile import profile_dataframe
from borges.analysis.scale_check import scale_check
from borges.analysis.smoke_review import llm_reviewer
from borges.config import Settings
from borges.garden.executor import GardenExecutor
from borges.garden.influence import build_report
from borges.garden.models import Flip, Garden, Report, SearchSummary, Universe
from borges.garden.search import combination_flip_choices, minimal_flip, single_flip_choices
from borges.llm.client import BudgetExceeded, LLMClient, UsageTotals
from borges.runs.adversary_round import run_adversary_round
from borges.runs.emitter import RunEmitter
from borges.runs.inputs import ResolvedRun
from borges.runs.judged_ledger import JudgedLedger
from borges.runs.pipeline_callbacks import coding_callbacks
from borges.runs.pipeline_caveats import report_caveats
from borges.runs.pipeline_data import load_dataframe
from borges.runs.pipeline_finish import narrate_stage, verify_stage
from borges.runs.plan_judging import judge_plan_options
from borges.runs.runner import UniverseRunner, publish_plan
from borges.sandbox.backend import BranchBackend
from borges.telemetry import hooks

MAX_COMBINATIONS_PER_LEVEL = 10


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
        self.caveats: list[str] = []
        self.coding = CodingSummary()
        self.judged = JudgedLedger()
        self.smoke: SmokeConfig | None = None
        self.search = SearchSummary(
            max_combinations_per_level=MAX_COMBINATIONS_PER_LEVEL,
            universe_budget=resolved.max_universes,
        )
        emitter.usage_probe = self._usage

    def _usage(self) -> tuple[UsageTotals, int]:
        created = self.executor.checkpoints_created if self.executor else 0
        return self.llm.totals, created

    @asynccontextmanager
    async def stage(self, name: str, detail: str = "") -> AsyncIterator[None]:
        with hooks.span("stage", f"stage {name}", **{"borges.stage": name}):
            await self.emitter.stage(name, "started", detail)
            yield
            await self.emitter.stage(name, "done")
            await self.emitter.usage()

    async def _plan(self) -> AnalysisPlan:
        resolved = self.resolved
        async with self.stage("profiling"):
            frame = load_dataframe(resolved.data)
            profile = await asyncio.to_thread(
                profile_dataframe,
                frame,
                resolved.dataset_name,
                column_notes=resolved.column_notes,
            )
        async with self.stage("planning"):
            plan = await plan_analysis(self.llm, profile, resolved.question, resolved.decision_rule)
            await publish_plan(self.emitter, plan)
            await judge_plan_options(self.llm, plan, self.emitter, self.coding, self.judged)

        on_coded, on_smoke, on_review = coding_callbacks(self.emitter)
        smoke = SmokeConfig(
            self.backend,
            resolved.data,
            on_smoke,
            self.settings.borges_step_timeout_s,
            reviewer=llm_reviewer(self.llm, plan),
            on_review=on_review,
            result_check=scale_check(plan.decision_rule),
            result_scale=plan.result_scale,
        )
        self.smoke = smoke
        async with self.stage("coding"):
            plan = await code_plan(
                self.llm,
                plan,
                on_coded,
                self.settings.borges_concurrency,
                smoke=smoke,
                summary=self.coding,
            )
            await publish_plan(self.emitter, plan)
        self.caveats.extend(smoke.state.notes)
        return plan

    async def _search(self, plan: AnalysisPlan) -> None:
        executor = GardenExecutor(
            self.backend,
            plan,
            self.resolved.data,
            self.emitter.emit,
            self.settings.borges_concurrency,
            step_timeout_s=self.settings.borges_step_timeout_s,
        )
        self.executor = executor
        await executor.setup()
        runner = UniverseRunner(
            self.llm, plan, executor, self.garden, self.emitter, self.resolved.max_universes
        )
        async with self.stage("baseline"):
            baseline = await runner.run(plan.default_choices(), "baseline")
            if baseline.status != "done":
                raise RuntimeError(f"the baseline analysis failed: {baseline.error}")
        async with self.stage("single_flips"):
            singles = single_flip_choices(plan)
            if len(singles) > runner.remaining:
                self.search.budget_exhausted = True
                self.caveats.append(
                    "The universe budget ran out before every single-decision flip was tried."
                )
            self.search.levels_explored = 1
            await self._tolerate_budget(
                runner.run_many(singles, "single"), "The single-decision flips stopped early"
            )
        if runner.remaining > 0:
            await self._adversary(plan, runner, baseline)
        else:
            self.search.budget_exhausted = True
            self.caveats.append("The universe budget ran out before the adversary stage ran.")
        self.flip = minimal_flip(plan, self.garden)
        if self.flip is None and runner.remaining > 0:
            await self._tolerate_budget(
                self._combinations(plan, runner), "The combination flips stopped early"
            )
        elif self.flip is None and len(plan.decision_steps) > 1:
            self.search.budget_exhausted = True
        self.search.universes_used = len(self.garden.universes)

    async def _tolerate_budget(self, work: Awaitable[object], label: str) -> None:
        try:
            await work
        except BudgetExceeded as exc:
            self.search.budget_exhausted = True
            self.caveats.append(f"{label} because the spend or run cap was reached: {exc}")

    async def _adversary(
        self, plan: AnalysisPlan, runner: UniverseRunner, baseline: Universe
    ) -> None:
        async with self.stage("adversary"):
            try:
                await run_adversary_round(
                    self.llm, plan, runner, self.emitter, baseline, self.smoke, self.judged
                )
            except Exception as exc:
                self.caveats.append(f"The adversary stage failed and was skipped: {exc}")

    async def _combinations(self, plan: AnalysisPlan, runner: UniverseRunner) -> None:
        async with self.stage("combination_flips"):
            for size in range(2, len(plan.decision_steps) + 1):
                if self.flip is not None:
                    break
                if runner.remaining <= 0:
                    self.search.budget_exhausted = True
                    break
                limit = min(MAX_COMBINATIONS_PER_LEVEL, runner.remaining)
                choices = combination_flip_choices(plan, self.garden, size, limit)
                if not choices:
                    break
                self.search.levels_explored = size
                await self.emitter.stage("combination_flips", "started", f"{size} changes")
                await runner.run_many(choices, "combination")
                self.flip = minimal_flip(plan, self.garden)

    async def run(self) -> Report:
        plan = await self._plan()
        await self._search(plan)
        await verify_stage(self, plan)
        self.report = build_report(plan, self.garden, self.flip)
        self.report.search = self.search
        self.report.coding = self.coding if self.coding.options else None
        self.caveats.extend(report_caveats(self.report, self.flip, plan.decision_rule.threshold))
        self.report.caveats = [*self.caveats, *self.report.caveats]
        await narrate_stage(self, plan, self.report)
        return self.report
