from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from borges.analysis.models import AnalysisPlan, AnalysisResult, Proposal, StepTrace
from borges.garden.models import Universe
from tests.runs.fakes import RULE

BASE_ESTIMATE = 1.0


@dataclass
class Scenario:
    effects: dict[tuple[str, str], float] = field(
        default_factory=lambda: {("s1", "b"): -0.5, ("s2", "y"): -1.2, ("s2", "adv"): -2.0}
    )
    broken: set[tuple[str, str]] = field(default_factory=set)
    unrepairable: bool = False
    repair_error: Exception | None = None
    proposals: list[Proposal] = field(default_factory=list)
    accept: bool = True
    narrate_error: Exception | None = None
    propose_error: Exception | None = None
    judge_errors: set[str] = field(default_factory=set)
    verify_error: Exception | None = None
    reproduced: bool | None = True
    plan_error: Exception | None = None
    hang: bool = False
    entered_plan: asyncio.Event = field(default_factory=asyncio.Event)
    combination_choices: list[dict[str, str]] = field(default_factory=list)
    executors: list[FakeExecutor] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    combination_calls: list[tuple[int, int]] = field(default_factory=list)


class FakeExecutor:
    scenario: Scenario

    def __init__(
        self,
        backend: Any,
        plan: AnalysisPlan,
        data: bytes,
        emit: Any,
        concurrency: int,
        **kwargs: Any,
    ):
        self.kwargs = kwargs
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
