from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Step
from borges.analysis.plan_refill import collapsed_steps, propose_refill
from borges.analysis.schemas import PlannedOption, ReplanOutput
from borges.llm.client import Role
from tests.analysis.fakes import FakeLLM
from tests.runs.fakes import make_option, make_plan


def wide_plan(alternatives: dict[str, int]) -> AnalysisPlan:
    steps = [
        Step(
            id=step_id,
            title=f"Step {step_id}",
            kind="model" if step_id == "m" else "feature",
            description="",
            options=[make_option(f"{step_id}0", True)]
            + [make_option(f"{step_id}{i}") for i in range(1, count)],
        )
        for step_id, count in alternatives.items()
    ]
    return make_plan().model_copy(update={"steps": steps})


def test_steps_left_with_one_option_are_refilled_when_too_few_steps_branch() -> None:
    plan = wide_plan({"a": 1, "b": 2, "c": 1, "m": 1})
    before = {"a": 2, "b": 2, "c": 2, "m": 3}
    assert [s.id for s in collapsed_steps(plan, before)] == ["a", "c", "m"]


def test_nothing_is_refilled_when_enough_steps_still_branch() -> None:
    plan = wide_plan({"a": 1, "b": 2, "c": 2, "m": 2})
    assert collapsed_steps(plan, {"a": 2, "b": 2, "c": 2, "m": 2}) == []


def test_nothing_is_refilled_when_the_planner_offered_too_few_branching_steps() -> None:
    plan = wide_plan({"a": 1, "m": 2})
    assert collapsed_steps(plan, {"a": 2, "m": 2}) == []


def planned(*items: tuple[str, str, bool]) -> ReplanOutput:
    return ReplanOutput(
        options=[
            PlannedOption(id=i, label=f"L {i}", rationale="r", spec=spec, is_default=default)
            for i, spec, default in items
        ]
    )


async def test_new_alternatives_are_non_default_novel_and_capped() -> None:
    plan = wide_plan({"a": 1, "m": 1})
    step = plan.step("a")
    rejected = [(make_option("a1"), "a fixed 0.5 cut-off has no basis in the rating scale")]
    out = planned(
        ("a1", "spec a1", False),
        ("a0", "Spec   A0", False),
        ("tercile", "split at the terciles", True),
        ("q", "split at the quartiles", False),
        ("z", "z-score", False),
    )
    llm = FakeLLM({"planner:refill:a": out})
    options = await propose_refill(llm, plan, step, rejected)
    assert [o.id for o in options] == ["tercile", "q"]
    assert not any(o.is_default for o in options)
    assert all(o.origin == "planner" for o in options)
    call = llm.calls[0]
    assert call.role is Role.PLANNER and call.schema is ReplanOutput
    content = call.messages[1]["content"]
    assert "a fixed 0.5 cut-off has no basis in the rating scale" in content
    assert '"spec":"spec a0"' in content and "Step a (feature)" in content


async def test_ids_already_taken_are_renamed() -> None:
    plan = wide_plan({"a": 1, "m": 1})
    llm = FakeLLM({"planner:refill:a": planned(("a1", "a new spec", False))})
    options = await propose_refill(llm, plan, plan.step("a"), [(make_option("a1"), "no")])
    assert [o.id for o in options] == ["a1_2"]


async def test_a_planner_failure_adds_nothing() -> None:
    plan = wide_plan({"a": 1, "m": 1})
    assert await propose_refill(FakeLLM({}), plan, plan.step("a"), []) == []


async def test_a_refill_that_builds_its_result_under_another_name_is_left_out() -> None:
    plan = wide_plan({"a": 1, "m": 1})
    step = plan.step("a")
    default = step.options[0].model_copy(update={"spec": "Create 'log_y' = log1p(outcome)."})
    step = step.model_copy(update={"options": [default], "produces": ["log_y"]})
    plan = plan.model_copy(update={"steps": [step, plan.step("m")]})
    out = planned(
        ("sqrt", "Create new column 'sqrt_y' = np.sqrt(outcome).", False),
        ("asinh", "Create 'log_y' = np.arcsinh(outcome).", False),
    )
    llm = FakeLLM({"planner:refill:a": out})
    options = await propose_refill(llm, plan, step, [(make_option("a1"), "no")])
    assert [o.id for o in options] == ["asinh"]
