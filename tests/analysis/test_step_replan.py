from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.analysis.smoke_types import Outcome
from borges.analysis.step_replan import propose_options, replan_key
from borges.llm.client import Role
from tests.analysis.fakes import FakeLLM, make_option, make_plan


def failed(option_id: str, error: str) -> Outcome:
    return Outcome(make_option(option_id), "failed", 3, error, None, [])


def reply(*options: dict) -> dict:
    return {"options": list(options)}


def planned(option_id: str, default: bool = False) -> dict:
    return {
        "id": option_id,
        "label": f"L {option_id}",
        "rationale": "r",
        "spec": f"spec {option_id}",
        "is_default": default,
    }


def plan_with_produces() -> AnalysisPlan:
    plan = make_plan()
    plan.step("d1").produces = ["clean_outcome"]
    return plan


async def test_replacement_options_keep_the_step_and_get_fresh_unique_ids() -> None:
    plan = plan_with_produces()
    step = plan.step("m1")
    llm = FakeLLM(
        {
            replan_key("m1"): reply(
                planned("OLS cluster!", False),
                planned("ols", True),
                planned("OLS cluster!", False),
            )
        }
    )
    outcomes = [failed("ols", "weights NaN"), failed("welch", "rank-deficient")]
    options = await propose_options(llm, plan, step, outcomes)
    assert options is not None
    assert [o.id for o in options] == ["ols_cluster", "ols_2", "ols_cluster_2"]
    assert [o.is_default for o in options] == [False, True, False]
    assert all(o.code is None and o.origin == "planner" for o in options)
    assert llm.calls[0].role is Role.PLANNER and llm.keys() == ["planner:replan:m1"]


async def test_the_first_option_is_the_default_when_none_is_marked() -> None:
    plan = make_plan()
    llm = FakeLLM({replan_key("m1"): reply(planned("a"), planned("b"))})
    options = await propose_options(llm, plan, plan.step("m1"), [failed("ols", "x")])
    assert options is not None and [o.is_default for o in options] == [True, False]


async def test_only_the_first_default_is_kept() -> None:
    plan = make_plan()
    llm = FakeLLM({replan_key("m1"): reply(planned("a", True), planned("b", True))})
    options = await propose_options(llm, plan, plan.step("m1"), [failed("ols", "x")])
    assert options is not None and [o.is_default for o in options] == [True, False]


async def test_the_prompt_carries_errors_columns_and_levels() -> None:
    plan = plan_with_produces()
    llm = FakeLLM({replan_key("m1"): reply(planned("a"))})
    await propose_options(llm, plan, plan.step("m1"), [failed("ols", "Singular matrix xyz")])
    prompt = llm.calls[0].messages[1]["content"]
    assert "Singular matrix xyz" in prompt and "Spec for ols on outcome" in prompt
    assert '"name":"group","dtype":"object","n_unique":2' in prompt
    assert '"name":"outcome","dtype":"float64"}' in prompt
    assert '"name":"clean_outcome","produced_earlier":true' in prompt
    assert "Mean difference in outcome between groups" in prompt
    assert "never dummy fixed effects" in llm.calls[0].messages[0]["content"]


async def test_a_missing_scripted_key_gives_no_replacement() -> None:
    plan = make_plan()
    llm = FakeLLM({})
    assert await propose_options(llm, plan, plan.step("m1"), [failed("ols", "x")]) is None
    assert llm.keys() == ["planner:replan:m1"]


async def test_a_reply_without_options_gives_no_replacement() -> None:
    plan = make_plan()
    llm = FakeLLM({replan_key("m1"): reply()})
    assert await propose_options(llm, plan, plan.step("m1"), [failed("ols", "x")]) is None


async def test_an_option_repeating_a_failed_spec_is_dropped_under_a_new_id() -> None:
    plan = make_plan()
    step = plan.step("m1")
    repeated = planned("fresh_id")
    repeated["spec"] = "  " + failed("ols", "x").option.spec.upper() + " "
    llm = FakeLLM({replan_key("m1"): reply(repeated, planned("other"))})
    options = await propose_options(llm, plan, step, [failed("ols", "x")])
    assert options is not None and [o.id for o in options] == ["other"]


async def test_a_reply_that_only_repeats_failed_specs_gives_no_replacement() -> None:
    plan = make_plan()
    repeated = planned("again")
    repeated["spec"] = failed("ols", "x").option.spec
    llm = FakeLLM({replan_key("m1"): reply(repeated)})
    assert await propose_options(llm, plan, plan.step("m1"), [failed("ols", "x")]) is None


async def test_at_most_four_replacements_are_kept() -> None:
    plan = make_plan()
    llm = FakeLLM({replan_key("m1"): reply(*(planned(f"o{i}") for i in range(7)))})
    options = await propose_options(llm, plan, plan.step("m1"), [failed("ols", "x")])
    assert options is not None and len(options) == 4


async def test_replanned_option_referring_to_a_sibling_is_expanded() -> None:
    plan = make_plan()
    sibling = dict(planned("base_fit", True), spec="Poisson GLM with offset")
    follower = dict(planned("clustered"), spec="Same as base_fit but cluster by referee")
    llm = FakeLLM({replan_key("m1"): reply(sibling, follower)})
    options = await propose_options(llm, plan, plan.step("m1"), [failed("ols", "x")])
    assert options is not None
    assert "(base_fit: Poisson GLM with offset)" in options[1].spec
    assert options[0].spec == "Poisson GLM with offset"
