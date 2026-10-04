from __future__ import annotations

from typing import Literal

from borges.analysis.models import AnalysisPlan, CodingSummary, DatasetProfile, Option, Proposal
from borges.armor.audit import record_decision, record_report
from borges.armor.option_guard import option_findings, poison_decision, poison_reason, screen_plan
from borges.armor.profile_guard import guard_profile
from borges.armor.report import ArmorReport
from borges.armor.second_stage import second_stage
from borges.config import Settings
from borges.llm.client import LLMClient
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionJudgedData
from borges.runs.runner import publish_plan


class ArmorStage:
    """Armor checkpoints of one run: what models read about the data, and what they propose."""

    def __init__(
        self,
        settings: Settings,
        llm: LLMClient,
        emitter: RunEmitter,
        report: ArmorReport,
        summary: CodingSummary,
    ) -> None:
        self.settings = settings
        self.llm = llm
        self.emitter = emitter
        self.report = report
        self.summary = summary

    def record(self, other: ArmorReport) -> None:
        self.report.extend(other)
        record_report(other)

    async def profile(self, profile: DatasetProfile) -> DatasetProfile:
        guarded, found = guard_profile(profile)
        self.record(found)
        if not self.settings.borges_armor_llm:
            return guarded
        extra = ArmorReport()
        reviewed = await second_stage(self.llm, guarded, extra)
        self.record(extra)
        return reviewed

    async def _drop(
        self, step_id: str, option_id: str, origin: Literal["planner", "adversary"], reason: str
    ) -> None:
        data = OptionJudgedData(
            step_id=step_id,
            option_id=option_id,
            defensibility=0.0,
            accepted=False,
            reason=reason,
            origin=origin,
        )
        await self.emitter.emit("option.judged", data.model_dump(mode="json"))
        self.summary.options_dropped_by_armor += 1

    async def plan(self, plan: AnalysisPlan) -> AnalysisPlan:
        flagged, found = screen_plan(plan)
        self.record(found)
        if not flagged:
            return plan
        for (step_id, option_id), findings in flagged.items():
            await self._drop(step_id, option_id, "planner", poison_reason(findings))
        for step in plan.steps:
            step.options = [o for o in step.options if (step.id, o.id) not in flagged]
        await publish_plan(self.emitter, plan)
        return plan

    async def _passes(
        self, step_id: str, option: Option, origin: Literal["planner", "adversary"]
    ) -> bool:
        findings = option_findings(option)
        if not findings:
            return True
        decision = poison_decision(f"{origin}:{step_id}.{option.id}", "drop", findings)
        self.report.add(decision)
        record_decision(decision)
        await self._drop(step_id, option.id, origin, poison_reason(findings))
        return False

    async def proposals(self, proposals: list[Proposal]) -> list[Proposal]:
        return [p for p in proposals if await self._passes(p.step_id, p.option, "adversary")]

    async def planner_options(self, step_id: str, options: list[Option]) -> list[Option]:
        return [o for o in options if await self._passes(step_id, o, "planner")]
