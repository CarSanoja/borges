from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence

import pytest

from borges.analysis import harness as real_harness
from borges.analysis.models import (
    AnalysisPlan,
    AnalysisResult,
    DatasetProfile,
    DecisionRule,
    Option,
    Step,
    StepTrace,
)
from borges.garden import executor as executor_module
from borges.garden import executor_errors as executor_errors_module
from borges.garden import executor_output as executor_output_module
from borges.garden import verify as verify_module
from borges.garden.executor import GardenExecutor
from borges.garden.models import Garden
from borges.sandbox.backend import Checkpoint, ExecResult

EFFECTS: dict[tuple[str, str], float] = {
    ("s1", "b"): -0.5,
    ("s2", "y"): -1.2,
    ("s3", "n"): -0.3,
    ("s3", "o"): -2.1,
}
BASE_ESTIMATE = 1.0
HALF_WIDTH = 0.2
P_VALUE = 0.01


def make_plan() -> AnalysisPlan:
    def option(oid: str, default: bool = False, defensibility: float | None = None) -> Option:
        return Option(
            id=oid,
            label=f"label {oid}",
            rationale=f"why {oid}",
            spec=f"spec {oid}",
            is_default=default,
            defensibility=defensibility,
            source="src" if defensibility else None,
        )

    return AnalysisPlan(
        question="does it ship?",
        estimand="mean diff",
        decision_rule=DecisionRule(metric="diff", threshold=0.0),
        dataset=DatasetProfile(name="d", n_rows=10, columns=[]),
        steps=[
            Step(
                id="s1",
                title="Filter",
                kind="filter",
                description="",
                options=[option("a", True), option("b")],
            ),
            Step(
                id="s2",
                title="Transform",
                kind="transform",
                description="",
                options=[option("x", True), option("y", defensibility=0.5)],
            ),
            Step(
                id="s3",
                title="Model",
                kind="model",
                description="",
                options=[
                    option("m", True),
                    option("n", defensibility=0.6),
                    option("o", defensibility=0.9),
                ],
            ),
        ],
    )


def estimate_for(choices: Mapping[str, str]) -> float:
    return BASE_ESTIMATE + sum(EFFECTS.get(item, 0.0) for item in choices.items())


def result_for(choices: Mapping[str, str]) -> AnalysisResult:
    est = estimate_for(choices)
    return AnalysisResult(
        estimate=est, ci_low=est - HALF_WIDTH, ci_high=est + HALF_WIDTH, p_value=P_VALUE, n=100
    )


class FakeBackend:
    name = "fake"

    def __init__(self, plan: AnalysisPlan, fail: set[tuple[str, str]] | None = None) -> None:
        self.plan = plan
        self.fail = fail or set()
        self.runs: list[tuple[str, str]] = []
        self.root_calls = 0
        self._choices: dict[str, dict[str, str]] = {}
        self._counter = 0

    async def root(self, files: Mapping[str, bytes]) -> Checkpoint:
        self.root_calls += 1
        checkpoint = Checkpoint(id=self._next_id(), parent_id=None, backend=self.name)
        self._choices[checkpoint.id] = {}
        return checkpoint

    def _next_id(self) -> str:
        self._counter += 1
        return f"cp{self._counter}"

    async def run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None = None,
        timeout_s: float = 120.0,
    ) -> ExecResult:
        await asyncio.sleep(0)
        step_id, option_id = command[-1].split(":")
        self.runs.append((parent.id, command[-1]))
        child = Checkpoint(id=self._next_id(), parent_id=parent.id, backend=self.name)
        chosen = {**self._choices[parent.id], step_id: option_id}
        self._choices[child.id] = chosen
        if (step_id, option_id) in self.fail:
            return ExecResult(child, 1, "ERROR boom", "boom: traceback line", 0.0)
        lines = [f"TRACE {step_id} {option_id}"]
        if step_id == self.plan.steps[-1].id:
            r = result_for(chosen)
            lines.append(f"RESULT {r.estimate} {r.ci_low} {r.ci_high} {r.p_value} {r.n}")
        return ExecResult(child, 0, "\n".join(lines), "", 0.5)


def _parse_output(stdout: str) -> tuple[list[StepTrace], AnalysisResult | None]:
    traces: list[StepTrace] = []
    result: AnalysisResult | None = None
    for line in stdout.splitlines():
        parts = line.split()
        if parts[0] == "TRACE":
            traces.append(
                StepTrace(step_id=parts[1], option_id=parts[2], rows_before=10, rows_after=9)
            )
        elif parts[0] == "RESULT":
            est, low, high, p, n = (float(v) for v in parts[1:])
            result = AnalysisResult(estimate=est, ci_low=low, ci_high=high, p_value=p, n=int(n))
    return traces, result


def install_fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeHarness:
        DATA_FILE = real_harness.DATA_FILE

        @staticmethod
        def step_filename(step_id: str, option_id: str) -> str:
            return f"{step_id}_{option_id}.py"

        @staticmethod
        def render_step(
            step: Step,
            option: Option,
            design_check: bool = True,
            standardised: bool = False,
            full_data_checks: bool = False,
            row_key: str | None = None,
        ) -> str:
            return f"{step.id}:{option.id}"

        @staticmethod
        def step_command(step_id: str, option_id: str) -> list[str]:
            return ["python", f"{step_id}:{option_id}"]

        parse_output = staticmethod(_parse_output)

        @staticmethod
        def parse_error(stdout: str) -> str | None:
            return stdout if stdout.startswith("ERROR") else None

    monkeypatch.setattr(executor_module, "harness", FakeHarness)
    monkeypatch.setattr(executor_errors_module, "harness", FakeHarness)
    monkeypatch.setattr(executor_output_module, "harness", FakeHarness)
    monkeypatch.setattr(verify_module, "harness", FakeHarness)


async def build_garden(
    plan: AnalysisPlan, backend: FakeBackend, with_pairs: bool = False
) -> tuple[GardenExecutor, Garden]:
    from borges.garden.search import combination_flip_choices, single_flip_choices

    executor = GardenExecutor(backend, plan, b"data")
    await executor.setup()
    garden = Garden()
    base = await executor.run_universe(plan.default_choices(), "baseline")
    garden.add(base)
    garden.baseline_id = base.id
    for choices in single_flip_choices(plan):
        garden.add(await executor.run_universe(choices, "single"))
    if with_pairs:
        for choices in combination_flip_choices(plan, garden, 2, 10):
            garden.add(await executor.run_universe(choices, "combination"))
    return executor, garden
