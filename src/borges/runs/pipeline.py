from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from borges.analysis.coder import code_plan
from borges.analysis.coder_smoke import SmokeConfig
from borges.analysis.models import AnalysisPlan, CodingSummary
from borges.analysis.planner import plan_analysis
from borges.analysis.profile import blind_profile, profile_dataframe
from borges.analysis.scale_check import scale_check
from borges.analysis.smoke_review import llm_reviewer
from borges.armor.report import ArmorReport
from borges.config import Settings
from borges.fleet.models import RunAgents
from borges.garden.aliased import aliased_caveats, tangled_caveats
from borges.garden.covariate_sample import baseline_sample_caveats, covariate_sample_caveats
from borges.garden.discrete_quantile import discrete_quantile_caveats
from borges.garden.executor import GardenExecutor
from borges.garden.failed_caveat import failed_caveat
from borges.garden.hc_variant import hc_variant_caveats
from borges.garden.influence import build_report
from borges.garden.models import Flip, Garden, Report, SearchSummary
from borges.garden.outcome_scale import scale_note
from borges.garden.scaled_outcome import scaled_outcome_caveats
from borges.llm.client import LLMClient, UsageTotals
from borges.memory.run_memory import RunMemory
from borges.runs.emitter import RunEmitter
from borges.runs.inputs import ResolvedRun
from borges.runs.judged_ledger import JudgedLedger
from borges.runs.pipeline_armor import ArmorStage
from borges.runs.pipeline_callbacks import coding_callbacks, replan_callback
from borges.runs.pipeline_caveats import merge_caveats, report_caveats
from borges.runs.pipeline_data import load_dataframe
from borges.runs.pipeline_finish import narrate_stage, verify_stage
from borges.runs.pipeline_memory import finish_memory, prefill_code, recall_profile
from borges.runs.pipeline_search import search_garden
from borges.runs.pipeline_stages import (
    MAX_COMBINATIONS_PER_LEVEL,
)
from borges.runs.plan_judging import judge_plan_options
from borges.runs.runner import publish_plan
from borges.runtime.context import RunContext
from borges.runtime.stage_checkpoints import CODED_KEY, PLAN_KEY, coded_payload, plan_payload
from borges.runtime.universe_checkpoint import RestoredUniverses
from borges.sandbox.backend import BranchBackend
from borges.telemetry import hooks

BLIND_CAVEAT = (
    "Blind-notes run: the column notes and value descriptions were hidden from every agent, so "
    "what the agents proposed came from the data alone."
)


class Pipeline:
    """The whole analysis of ARCHITECTURE.md section 3, emitting the events of section 5."""

    def __init__(
        self,
        settings: Settings,
        llm: LLMClient,
        backend: BranchBackend,
        emitter: RunEmitter,
        resolved: ResolvedRun,
        armor: ArmorReport | None = None,
        memory: RunMemory | None = None,
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
        self.agents: RunAgents | None = None
        self.caveats: list[str] = []
        self.coding = CodingSummary()
        self.judged = JudgedLedger()
        self.memory = memory
        self.armor = armor if armor is not None else ArmorReport()
        self.armor_stage = ArmorStage(settings, llm, emitter, self.armor, self.coding)
        self.smoke: SmokeConfig | None = None
        self.context: RunContext | None = None
        self.restored: RestoredUniverses | None = None
        self.search = SearchSummary(
            max_combinations_per_level=MAX_COMBINATIONS_PER_LEVEL,
            universe_budget=resolved.max_universes,
        )
        emitter.usage_probe = self._usage

    def _usage(self) -> tuple[UsageTotals, int]:
        created = self.executor.checkpoints_created if self.executor else 0
        if self.context is not None and self.context.resumed:
            created = self.emitter.persisted_count("checkpoint.created")
        return self.llm.totals, created

    def checkpoint(self, key: str, payload: dict[str, Any]) -> None:
        if self.context is not None:
            self.context.save(key, self.emitter.seq, payload)

    @asynccontextmanager
    async def stage(self, name: str, detail: str = "") -> AsyncIterator[None]:
        replayed = self.emitter.has_pending("stage", {"name": name, "status": "done", "detail": ""})
        if self.context is not None:
            self.context.check()
        with hooks.span("stage", f"stage {name}", **{"borges.stage": name}):
            await self.emitter.stage(name, "started", detail)
            yield
            await self.emitter.stage(name, "done")
            if not replayed:
                await self.emitter.usage()
        if self.context is not None:
            self.context.check()

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
            profile = recall_profile(self, profile)
            if resolved.blind_notes:
                profile = blind_profile(profile)
                self.caveats.append(BLIND_CAVEAT)
            self.armor_stage.record(resolved.armor)
            profile = await self.armor_stage.profile(profile)
        async with self.stage("planning"):
            plan = await plan_analysis(self.llm, profile, resolved.question, resolved.decision_rule)
            plan = await self.armor_stage.plan(plan)
            await publish_plan(self.emitter, plan)
            await judge_plan_options(
                self.llm,
                plan,
                self.emitter,
                self.coding,
                self.judged,
                self.memory,
                self.armor_stage.planner_options,
            )
        self.checkpoint(PLAN_KEY, plan_payload(plan, self.judged, self.coding))

        on_coded, on_smoke, on_review = coding_callbacks(self.emitter)
        smoke = SmokeConfig(
            self.backend,
            resolved.data,
            on_smoke,
            self.settings.borges_step_timeout_s,
            reviewer=llm_reviewer(self.llm, plan),
            on_review=on_review,
            on_replan=replan_callback(self.emitter),
            result_check=scale_check(plan.decision_rule),
            result_scale=plan.result_scale,
            metric=plan.decision_rule.metric,
        )
        self.smoke = smoke
        async with self.stage("coding"):
            await prefill_code(self, plan, on_coded)
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
        self.checkpoint(CODED_KEY, coded_payload(plan, self.judged, self.coding, smoke.state.notes))
        return plan

    async def _search(self, plan: AnalysisPlan) -> None:
        await search_garden(self, plan)

    async def run(self) -> Report:
        plan: AnalysisPlan | None = None
        try:
            plan = await self._plan()
            await self._search(plan)
            await verify_stage(self, plan)
            await finish_memory(self, plan, announce=True)
        finally:
            await finish_memory(self, plan, announce=False)
        self.caveats.extend(self.armor.caveats())
        self.report = build_report(plan, self.garden, self.flip)
        self.report.search = self.search
        self.report.coding = self.coding if self.coding.options else None
        failed = failed_caveat(plan, self.garden)
        threshold = plan.decision_rule.threshold
        self.caveats.extend(report_caveats(self.report, self.flip, threshold, failed))
        self.caveats.extend(
            [
                *aliased_caveats(self.garden),
                *tangled_caveats(self.garden),
                *scaled_outcome_caveats(self.garden),
                *baseline_sample_caveats(plan, self.garden),
                *covariate_sample_caveats(plan, self.garden),
                *discrete_quantile_caveats(self.garden, self.flip and self.flip.universe_id),
                *hc_variant_caveats(self.garden),
            ]
        )
        note = scale_note(self.garden)
        if note is not None:
            self.caveats.append(note)
        self.report.caveats = merge_caveats(self.caveats, self.report.caveats)
        await narrate_stage(self, plan, self.report)
        return self.report
