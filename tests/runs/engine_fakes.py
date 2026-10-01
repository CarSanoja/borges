from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import pytest

from borges.analysis.models import (
    AnalysisPlan,
    AnalysisResult,
    DatasetProfile,
    Judgement,
    Option,
    Proposal,
    Step,
    StepTrace,
)
from borges.garden.models import Change, Flip, Garden, Report, Universe
from borges.runs import adversary_round, pipeline, runner
from tests.runs.fakes import RULE, make_plan

BASE_ESTIMATE = 1.0


@dataclass
class Scenario:
    effects: dict[tuple[str, str], float] = field(
        default_factory=lambda: {("s1", "b"): -0.5, ("s2", "y"): -1.2, ("s2", "adv"): -2.0}
    )
    broken: set[tuple[str, str]] = field(default_factory=set)
    unrepairable: bool = False
    proposals: list[Proposal] = field(default_factory=list)
    accept: bool = True
    narrate_error: Exception | None = None
    plan_error: Exception | None = None
    hang: bool = False
    entered_plan: asyncio.Event = field(default_factory=asyncio.Event)
    pair_choices: list[dict[str, str]] = field(default_factory=list)
    executors: list[FakeExecutor] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    pair_limits: list[int] = field(default_factory=list)


class FakeExecutor:
    scenario: Scenario

    def __init__(self, backend: Any, plan: AnalysisPlan, data: bytes, emit: Any, concurrency: int):
        self.plan = plan
        self.emit = emit
        self.baseline_verdict: str | None = None
        self.created = 0
        self.runs: list[tuple[dict[str, str], str]] = []
        self.scenario.executors.append(self)

    @property
    def checkpoints_created(self) -> int:
        return self.created

    async def setup(self) -> None:
        self.created += 1
        await self.emit(
            "checkpoint.created",
            {
                "checkpoint_id": "cp0",
                "parent_id": None,
                "step_id": None,
                "option_id": None,
                "depth": 0,
            },
        )

    async def run_universe(self, choices: dict[str, str], kind: str) -> Universe:
        full = {**self.plan.default_choices(), **choices}
        self.runs.append((full, kind))
        changed = [s.id for s in self.plan.steps if full[s.id] != s.default.id]
        uid = "u_" + "".join(f"{k}{v}" for k, v in sorted(full.items()))
        started = Universe(id=uid, choices=full, changed=changed, kind=kind, status="running")
        await self.emit("universe.started", {"universe": started.model_dump(mode="json")})
        checkpoints: list[str] = []
        traces: list[StepTrace] = []
        error = None
        for step in self.plan.steps:
            option = step.option(full[step.id])
            if (step.id, option.id) in self.scenario.broken and option.code != "fixed":
                error = f"{step.id}/{option.id}: boom"
                break
            self.created += 1
            checkpoints.append(f"cp_{step.id}_{option.id}")
            traces.append(
                StepTrace(step_id=step.id, option_id=option.id, rows_before=3, rows_after=3)
            )
        universe = started.model_copy(update={"checkpoints": checkpoints, "traces": traces})
        if error:
            universe.status, universe.error = "failed", error
        else:
            estimate = BASE_ESTIMATE + sum(
                self.scenario.effects.get((s, o), 0.0) for s, o in full.items()
            )
            result = AnalysisResult(
                estimate=estimate, ci_low=estimate - 0.1, ci_high=estimate + 0.1, p_value=0.01, n=3
            )
            verdict = RULE.label(result)
            if kind == "baseline":
                self.baseline_verdict = verdict
            universe.status, universe.result, universe.verdict = "done", result, verdict
            universe.flipped = kind != "baseline" and verdict != self.baseline_verdict
        await self.emit("universe.finished", {"universe": universe.model_dump(mode="json")})
        return universe


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

    def profile_dataframe(df: pd.DataFrame, name: str) -> DatasetProfile:
        scenario.calls.append("profile")
        return DatasetProfile(name=name, n_rows=len(df), columns=[])

    async def code_plan(llm: Any, plan: AnalysisPlan, on_coded: Any, concurrency: int):
        scenario.calls.append("code_plan")
        for step in plan.steps:
            for index, option in enumerate(step.options):
                step.options[index] = option.model_copy(update={"code": f"code-{option.id}"})
                await on_coded(step.id, option.id, True, 1, None)
        return plan

    async def repair_option(llm: Any, plan: AnalysisPlan, step: Step, option: Option, error: str):
        scenario.calls.append(f"repair:{step.id}.{option.id}:{error}")
        if scenario.unrepairable:
            raise RuntimeError("cannot repair")
        return option.model_copy(update={"code": "fixed"})

    async def propose_options(llm: Any, plan: AnalysisPlan, baseline: Universe):
        scenario.calls.append("propose")
        return scenario.proposals

    async def judge_option(llm: Any, plan: AnalysisPlan, step: Step, option: Option):
        return Judgement(
            defensibility=0.8, accepted=scenario.accept, reason="ok", source="http://s"
        )

    async def code_option(llm: Any, plan: AnalysisPlan, step: Step, option: Option) -> str:
        return f"code-{option.id}"

    def single_flip_choices(plan: AnalysisPlan) -> list[dict[str, str]]:
        defaults = plan.default_choices()
        return [
            {**defaults, s.id: o.id}
            for s in plan.decision_steps
            for o in s.options
            if not o.is_default
        ]

    def pair_flip_choices(plan: AnalysisPlan, garden: Garden, limit: int):
        scenario.pair_limits.append(limit)
        return scenario.pair_choices

    async def verify_flip(backend: Any, plan: Any, data: bytes, flip: Flip, garden: Garden) -> Flip:
        scenario.calls.append("verify")
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
        )

    async def narrate(llm: Any, plan: AnalysisPlan, report: Report):
        if scenario.narrate_error:
            raise scenario.narrate_error
        return "story", ["caveat"]

    patches: list[tuple[Any, str, Any]] = [
        (pipeline, "plan_analysis", plan_analysis),
        (pipeline, "profile_dataframe", profile_dataframe),
        (pipeline, "code_plan", code_plan),
        (pipeline, "GardenExecutor", FakeExecutor),
        (pipeline, "single_flip_choices", single_flip_choices),
        (pipeline, "pair_flip_choices", pair_flip_choices),
        (pipeline, "minimal_flip", fake_minimal_flip),
        (pipeline, "verify_flip", verify_flip),
        (pipeline, "build_report", build_report),
        (pipeline, "narrate", narrate),
        (runner, "repair_option", repair_option),
        (adversary_round, "propose_options", propose_options),
        (adversary_round, "judge_option", judge_option),
        (adversary_round, "code_option", code_option),
    ]
    for module, name, value in patches:
        monkeypatch.setattr(module, name, value)
