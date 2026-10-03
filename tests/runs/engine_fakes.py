from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import pytest

from borges.analysis.models import (
    AnalysisPlan,
    AnalysisResult,
    DatasetProfile,
    Judgement,
    Option,
    Step,
)
from borges.garden.influence import failed_universes
from borges.garden.models import Change, Flip, Garden, Report, Universe
from borges.llm.client import LLMError
from borges.runs import (
    adversary_round,
    pipeline,
    pipeline_finish,
    pipeline_search,
    pipeline_stages,
    plan_judging,
    runner,
)
from tests.runs.engine_scenario import FakeExecutor, Scenario
from tests.runs.fakes import make_plan


def _result(estimate: float) -> AnalysisResult:
    return AnalysisResult(estimate=estimate, ci_low=0, ci_high=0, p_value=0.01, n=3)


def fake_minimal_flip(plan: AnalysisPlan, garden: Garden) -> Flip | None:
    flipped = [u for u in garden.finished() if u.flipped]
    if not flipped:
        return None
    best = min(flipped, key=lambda u: len(u.changed))
    base = garden.baseline
    assert base is not None and base.result is not None and best.result is not None
    changes = [
        Change(
            step_id=s,
            step_title=s,
            from_option=plan.step(s).default.id,
            to_option=best.choices[s],
            to_label="l",
            rationale="r",
        )
        for s in best.changed
    ]
    return Flip(
        universe_id=best.id,
        changes=changes,
        baseline_result=base.result,
        flipped_result=best.result,
        baseline_verdict=base.verdict or "",
        flipped_verdict=best.verdict or "",
    )


def install(monkeypatch: pytest.MonkeyPatch, scenario: Scenario) -> None:
    FakeExecutor.scenario = scenario

    async def plan_analysis(llm: Any, profile: Any, question: str, rule: Any) -> AnalysisPlan:
        scenario.calls.append("plan_analysis")
        if scenario.plan_error:
            raise scenario.plan_error
        scenario.entered_plan.set()
        if scenario.hang:
            await asyncio.Event().wait()
        return make_plan()

    def profile_dataframe(df: pd.DataFrame, name: str, **_: Any) -> DatasetProfile:
        scenario.calls.append("profile")
        return DatasetProfile(name=name, n_rows=len(df), columns=[])

    async def code_plan(
        llm: Any, plan: AnalysisPlan, on_coded: Any, concurrency: int, **kwargs: Any
    ):
        scenario.calls.append("code_plan")
        for step in plan.steps:
            for index, option in enumerate(step.options):
                step.options[index] = option.model_copy(update={"code": f"code-{option.id}"})
                await on_coded(step.id, option.id, True, 1, None)
                smoke = kwargs.get("smoke")
                if smoke is not None and smoke.on_smoke is not None:
                    await smoke.on_smoke(step.id, option.id, "passed", 1, None)
        summary = kwargs.get("summary")
        if summary is not None:
            count = sum(len(step.options) for step in plan.steps)
            summary.options += count
            summary.smoke_tested += count
        return plan

    async def repair_option(llm: Any, plan: AnalysisPlan, step: Step, option: Option, error: str):
        scenario.calls.append(f"repair:{step.id}.{option.id}:{error}")
        if scenario.repair_error:
            raise scenario.repair_error
        if scenario.unrepairable:
            raise RuntimeError("cannot repair")
        return option.model_copy(update={"code": "fixed"})

    async def propose_options(llm: Any, plan: AnalysisPlan, baseline: Universe):
        scenario.calls.append("propose")
        if scenario.propose_error:
            raise scenario.propose_error
        return scenario.proposals

    async def judge_option(llm: Any, plan: AnalysisPlan, step: Step, option: Option):
        if option.id in scenario.judge_errors:
            raise LLMError(f"judge:{step.id}.{option.id}: invalid output")
        return Judgement(
            defensibility=0.8, accepted=scenario.accept, reason="ok", source="http://s"
        )

    async def judge_planner_option(
        llm: Any, plan: AnalysisPlan, step: Step, option: Option, origin: str = "adversary"
    ):
        scenario.planner_judged.append(f"{step.id}.{option.id}")
        accepted = option.id not in scenario.planner_rejects
        return Judgement(
            defensibility=0.8 if accepted else 0.2,
            accepted=accepted,
            reason="ok" if accepted else "no",
            source=None,
        )

    async def code_option(llm: Any, plan: AnalysisPlan, step: Step, option: Option) -> str:
        return f"code-{option.id}"

    async def review_proposal(
        llm: Any, plan: AnalysisPlan, emitter: Any, step: Step, option: Option
    ) -> Option:
        return option

    def single_flip_choices(plan: AnalysisPlan) -> list[dict[str, str]]:
        defaults = plan.default_choices()
        return [
            {**defaults, s.id: o.id}
            for s in plan.decision_steps
            for o in s.options
            if not o.is_default
        ]

    def combination_flip_choices(plan: AnalysisPlan, garden: Garden, size: int, limit: int):
        scenario.combination_calls.append((size, limit))
        return scenario.combination_choices if size == 2 else []

    async def verify_flip(
        backend: Any, plan: Any, data: bytes, flip: Flip, garden: Garden, **_: Any
    ) -> Flip:
        scenario.calls.append("verify")
        if scenario.verify_error:
            raise scenario.verify_error
        if scenario.reproduced is not True:
            return flip.model_copy(update={"reproduced": scenario.reproduced})
        return flip.model_copy(update={"reproduced": True, "reproduce_command": "python go.py"})

    def build_report(plan: AnalysisPlan, garden: Garden, flip: Flip | None) -> Report:
        base = garden.baseline
        assert base is not None and base.result is not None
        return Report(
            question=plan.question,
            original_verdict=base.verdict or "",
            original_result=base.result,
            minimal_flip=flip,
            influences=[],
            robustness=0.5,
            n_universes=len(garden.universes),
            n_flipped=sum(1 for u in garden.finished() if u.flipped),
            n_failed=len(failed_universes(garden)),
            failed=failed_universes(garden),
        )

    async def narrate(llm: Any, plan: AnalysisPlan, report: Report):
        if scenario.narrate_error:
            raise scenario.narrate_error
        return "story", ["caveat"]

    patches: list[tuple[Any, str, Any]] = [
        (pipeline, "plan_analysis", plan_analysis),
        (pipeline, "profile_dataframe", profile_dataframe),
        (pipeline, "code_plan", code_plan),
        (pipeline_search, "GardenExecutor", FakeExecutor),
        (pipeline_search, "single_flip_choices", single_flip_choices),
        (pipeline_stages, "combination_flip_choices", combination_flip_choices),
        (pipeline_search, "minimal_flip", fake_minimal_flip),
        (pipeline_stages, "minimal_flip", fake_minimal_flip),
        (pipeline_finish, "verify_flip", verify_flip),
        (pipeline, "build_report", build_report),
        (pipeline_finish, "narrate", narrate),
        (runner, "repair_option", repair_option),
        (adversary_round, "propose_options", propose_options),
        (adversary_round, "judge_option", judge_option),
        (plan_judging, "judge_option", judge_planner_option),
        (adversary_round, "code_option", code_option),
        (adversary_round, "review_proposal", review_proposal),
    ]
    for module, name, value in patches:
        monkeypatch.setattr(module, name, value)
