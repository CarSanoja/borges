from __future__ import annotations

from typing import Any

import pytest

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.garden.executor import universe_id
from borges.garden.models import Garden, Universe
from borges.runs.runner import UniverseRunner
from tests.runs.fakes import make_plan


class CodeExecutor:
    """Fails a universe whose s1 option carries the code 'broken'."""

    def __init__(self, plan: AnalysisPlan) -> None:
        self.plan = plan

    async def run_universe(self, choices: dict[str, str], kind: str) -> Universe:
        full = {**self.plan.default_choices(), **choices}
        code = self.plan.step("s1").option(full["s1"]).code
        failed = code == "broken"
        return Universe(
            id=universe_id(full),
            choices=full,
            kind=kind,
            status="failed" if failed else "done",
            error="KeyError: 'day'" if failed else None,
            checkpoints=[] if failed else ["c1", "c2"],
        )


class Emitter:
    def __init__(self) -> None:
        self.seq = 0
        self.universes_finished = 0
        self.events: list[str] = []

    async def emit(self, kind: str, data: dict[str, Any]) -> None:
        self.events.append(kind)


def runner_for(plan: AnalysisPlan, garden: Garden | None = None) -> tuple[UniverseRunner, Emitter]:
    emitter = Emitter()
    runner = UniverseRunner(None, plan, CodeExecutor(plan), garden or Garden(), emitter, 20)
    return runner, emitter


def with_codes(b: str) -> AnalysisPlan:
    plan = make_plan()
    for step in plan.steps:
        step.options = [o.model_copy(update={"code": f"code-{o.id}"}) for o in step.options]
    plan.step("s1").options[1] = plan.step("s1").option("b").model_copy(update={"code": b})
    return plan


def patch_repair(monkeypatch: pytest.MonkeyPatch, code: str, calls: list[str]) -> None:
    async def repair(llm: Any, plan: AnalysisPlan, step: Step, option: Option, error: str):
        calls.append(f"{step.id}.{option.id}")
        return option.model_copy(update={"code": code})

    monkeypatch.setattr("borges.runs.runner.repair_option", repair)


async def test_a_fresh_option_is_repaired_and_the_universe_rerun(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    patch_repair(monkeypatch, "fixed", calls)
    plan = with_codes("broken")
    runner, emitter = runner_for(plan)
    universe = await runner.run({"s1": "b"}, "single")
    assert calls == ["s1.b"] and universe.status == "done"
    assert plan.step("s1").option("b").code == "fixed"
    assert emitter.events == ["option.coded", "plan.ready"]


async def test_an_option_other_universes_already_ran_is_not_rewritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    patch_repair(monkeypatch, "fixed", calls)
    plan = with_codes("broken")
    done = Universe(id="u_done", choices={"s1": "b", "s2": "x"}, kind="single", status="done")
    runner, emitter = runner_for(plan, Garden(universes={"u_done": done}))
    universe = await runner.run({"s1": "b", "s2": "y"}, "single")
    assert calls == [] and universe.status == "failed"
    assert plan.step("s1").option("b").code == "broken" and emitter.events == []


async def test_a_repair_that_returns_the_same_code_changes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    patch_repair(monkeypatch, "broken", calls)
    plan = with_codes("broken")
    runner, emitter = runner_for(plan)
    universe = await runner.run({"s1": "b"}, "single")
    assert calls == ["s1.b"] and universe.status == "failed" and emitter.events == []


async def test_a_repair_whose_rerun_fails_restores_the_previous_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    plan = with_codes("broken")

    async def repair(llm: Any, plan_: AnalysisPlan, step: Step, option: Option, error: str):
        calls.append(option.id)
        return option.model_copy(update={"code": "still broken"})

    monkeypatch.setattr("borges.runs.runner.repair_option", repair)

    class StillFails(CodeExecutor):
        async def run_universe(self, choices: dict[str, str], kind: str) -> Universe:
            universe = await super().run_universe(choices, kind)
            code = self.plan.step("s1").option(universe.choices["s1"]).code
            if code == "still broken":
                return universe.model_copy(update={"status": "failed", "error": "again"})
            return universe

    emitter = Emitter()
    runner = UniverseRunner(None, plan, StillFails(plan), Garden(), emitter, 20)
    universe = await runner.run({"s1": "b"}, "single")
    assert universe.status == "failed" and universe.error == "KeyError: 'day'"
    assert plan.step("s1").option("b").code == "broken"
    assert emitter.events == ["option.coded", "plan.ready", "option.coded", "plan.ready"]
