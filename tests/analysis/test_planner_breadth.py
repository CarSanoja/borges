from __future__ import annotations

from borges.analysis.models import ColumnProfile, DatasetProfile, DecisionRule
from borges.analysis.planner import plan_analysis
from borges.analysis.planner_validation import plan_shortfalls
from borges.analysis.prompts.planner import build_messages
from borges.analysis.schemas import PlannerOutput
from tests.analysis.fakes import FakeLLM, make_profile
from tests.analysis.test_planner import popt, pstep


def narrow() -> PlannerOutput:
    return PlannerOutput(
        estimand="E",
        steps=[
            pstep("trim", "filter", [popt("a", True)]),
            pstep("scale", "transform", [popt("a", True), popt("b")]),
            pstep("m", "model", [popt("ols", True), popt("welch")]),
        ],
    )


def broad() -> PlannerOutput:
    return PlannerOutput(
        estimand="E",
        steps=[
            pstep("trim", "filter", [popt("a", True), popt("b")]),
            pstep("scale", "transform", [popt("a", True), popt("b")]),
            pstep("m", "model", [popt("ols", True), popt("welch")]),
        ],
    )


def flagged_profile() -> DatasetProfile:
    return DatasetProfile(
        name="t",
        n_rows=100,
        columns=[
            ColumnProfile(name="group", dtype="object", n_missing=0, n_unique=2),
            ColumnProfile(
                name="is_internal",
                dtype="bool",
                n_missing=0,
                n_unique=2,
                summary={"share_true": 0.05},
            ),
        ],
    )


async def test_single_option_steps_trigger_one_reask_naming_them() -> None:
    class Seq(FakeLLM):
        async def complete(self, role, messages, **kw):  # type: ignore[no-untyped-def]
            self.responses["planner:retry"] = broad()
            return await super().complete(role, messages, **kw)

    llm = Seq({"planner": narrow()})
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    assert llm.keys() == ["planner", "planner:retry"]
    feedback = llm.calls[1].messages[-1]["content"]
    assert "trim" in feedback and "single option" in feedback
    assert llm.calls[1].messages[-2]["role"] == "assistant"
    assert [len(s.options) for s in plan.steps] == [2, 2, 2]


async def test_broad_plan_is_not_reasked() -> None:
    llm = FakeLLM({"planner": broad()})
    await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    assert llm.keys() == ["planner"]


async def test_failed_reask_accepts_first_plan() -> None:
    llm = FakeLLM({"planner": narrow()})
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    assert llm.keys() == ["planner", "planner:retry"]
    assert [s.id for s in plan.steps] == ["trim", "scale", "m"]


def test_too_few_branching_steps() -> None:
    out = PlannerOutput(
        estimand="E",
        steps=[
            pstep("f", "filter", [popt("a", True), popt("b")]),
            pstep("m", "model", [popt("ols", True), popt("welch")]),
        ],
    )
    assert any("at least 3" in p for p in plan_shortfalls(out.steps, make_profile()))


def test_missing_inclusion_step_reported_for_flag_column() -> None:
    problems = plan_shortfalls(broad().steps, flagged_profile())
    assert any("is_internal" in p and "data-inclusion" in p for p in problems)


def test_inclusion_step_naming_flag_column_satisfies() -> None:
    out = broad()
    out.steps[0].options[0].spec = "keep every row including is_internal sessions"
    assert plan_shortfalls(out.steps, flagged_profile()) == []


def test_flag_column_reaches_planner_prompt() -> None:
    content = build_messages(flagged_profile(), "Q?", DecisionRule(metric="m"))[1]["content"]
    assert "is_internal" in content and "5.0% of rows are true" in content
    assert "internal, staff, bot" in content


def test_prompt_without_flags_has_no_candidate_block() -> None:
    content = build_messages(make_profile(), "Q?", DecisionRule(metric="m"))[1]["content"]
    assert "look like flags" not in content


def test_outlier_column_listed() -> None:
    profile = DatasetProfile(
        name="t",
        n_rows=100,
        columns=[
            ColumnProfile(
                name="spend",
                dtype="float64",
                n_missing=0,
                n_unique=50,
                summary={"mean": 5.0, "std": 3.0, "min": 0.0, "p50": 4.0, "max": 900.0},
            )
        ],
    )
    content = build_messages(profile, "Q?", DecisionRule(metric="m"))[1]["content"]
    assert "extreme values" in content and "spend" in content


def test_scripted_plans_meet_the_rule() -> None:
    import json
    from pathlib import Path

    for case in ["checkout_ab", "red_cards", "marp_norms", "marp_religiosity"]:
        data = json.loads(Path(f"cases/{case}/fixtures/planner.json").read_text())
        out = PlannerOutput.model_validate(data["parsed"])
        problems = plan_shortfalls(out.steps, make_profile())
        assert [p for p in problems if "produces" not in p] == [], case


def no_model() -> PlannerOutput:
    return PlannerOutput(
        estimand="E",
        steps=[
            pstep("trim", "filter", [popt("a", True), popt("b")]),
            pstep("scale", "transform", [popt("a", True), popt("b")]),
            pstep("fit", "transform", [popt("a", True), popt("b")]),
        ],
    )


async def test_missing_model_step_is_reasked_once_with_feedback() -> None:
    class Seq(FakeLLM):
        async def complete(self, role, messages, **kw):  # type: ignore[no-untyped-def]
            self.responses["planner:retry"] = broad()
            return await super().complete(role, messages, **kw)

    llm = Seq({"planner": no_model()})
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    assert llm.keys() == ["planner", "planner:retry"]
    assert "kind 'model'" in llm.calls[1].messages[-1]["content"]
    assert plan.steps[-1].kind == "model"


async def test_missing_model_step_after_reask_still_fails() -> None:
    import pytest

    from borges.llm.client import LLMError

    llm = FakeLLM({"planner": no_model(), "planner:retry": no_model()})
    with pytest.raises(LLMError, match="no step of kind 'model'"):
        await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))


async def test_ids_from_the_model_are_normalised() -> None:
    out = PlannerOutput(
        estimand="E",
        steps=[
            pstep(
                " Trim Rows", "filter", [popt(" ols_demographics", True), popt("OLS-demographics")]
            ),
            pstep("scale", "transform", [popt("a", True), popt("b")]),
            pstep("m", "model", [popt(" ols ", True), popt("Welch T")]),
            pstep("trim_rows", "filter", [popt("x", True), popt("y")]),
        ],
    )
    plan = await plan_analysis(
        FakeLLM({"planner": out}), make_profile(), "Q?", DecisionRule(metric="m")
    )
    ids = [s.id for s in plan.steps]
    assert ids == ["trim_rows", "scale", "trim_rows_2", "m"]
    assert [o.id for o in plan.steps[0].options] == ["ols_demographics", "ols_demographics_2"]
    assert [o.id for o in plan.steps[-1].options] == ["ols", "welch_t"]


def undeclared() -> PlannerOutput:
    return PlannerOutput(
        estimand="E",
        steps=[
            pstep("trim", "filter", [popt("a", True), popt("b")]),
            pstep("scale", "transform", [popt("a", True), popt("b")], produces=[]),
            pstep("m", "model", [popt("ols", True), popt("welch")]),
        ],
    )


def test_transform_without_produces_is_a_shortfall() -> None:
    problems = plan_shortfalls(undeclared().steps, make_profile())
    assert len(problems) == 1 and "produces" in problems[0] and "scale" in problems[0]


def test_filter_without_produces_is_fine() -> None:
    assert plan_shortfalls(broad().steps, make_profile()) == []


async def test_missing_produces_triggers_one_reask_with_feedback() -> None:
    class Seq(FakeLLM):
        async def complete(self, role, messages, **kw):  # type: ignore[no-untyped-def]
            self.responses["planner:retry"] = broad()
            return await super().complete(role, messages, **kw)

    llm = Seq({"planner": undeclared()})
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    assert llm.keys() == ["planner", "planner:retry"]
    feedback = llm.calls[1].messages[-1]["content"]
    assert "produces" in feedback and "scale" in feedback
    assert [s.produces for s in plan.steps] == [[], ["scale_col"], []]


def two_models() -> PlannerOutput:
    return PlannerOutput(
        estimand="E",
        steps=[
            pstep("trim", "filter", [popt("a", True), popt("b")]),
            pstep("scale", "transform", [popt("a", True), popt("b")]),
            pstep("poisson", "model", [popt("glm", True), popt("negbin")]),
            pstep("binary", "model", [popt("logit", True), popt("logit_robust")]),
        ],
    )


def test_two_model_steps_are_a_shortfall() -> None:
    problems = plan_shortfalls(two_models().steps, make_profile())
    assert any("Only one step may have kind 'model'" in p for p in problems)


async def test_model_steps_left_after_the_reask_are_merged_into_one_final_step() -> None:
    llm = FakeLLM({"planner": two_models(), "planner:retry": two_models()})
    plan = await plan_analysis(llm, make_profile(), "Q?", DecisionRule(metric="m"))
    models = [s for s in plan.steps if s.kind == "model"]
    assert len(models) == 1 and plan.steps[-1] is models[0]
    assert [o.id for o in models[0].options] == ["glm", "negbin", "logit", "logit_robust"]
    assert [o.is_default for o in models[0].options] == [True, False, False, False]
