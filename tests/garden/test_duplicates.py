from __future__ import annotations

from borges.garden.duplicates import duplicate_options, excluded_options
from borges.garden.influence import build_report
from borges.garden.search import minimal_flip
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, universe


def adversary(oid: str):
    item = option(oid, label=f"adv {oid}")
    item.origin = "adversary"
    return item


def model_plan():
    return plan_of(
        step_of("model", "model", option("m", True), adversary("adv"), option("planner"))
    )


def test_adversary_equal_to_a_planner_option_is_the_duplicate() -> None:
    plan = model_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0)),
        universe(plan, {"model": "adv"}, result(-1.2538585445178378)),
        universe(plan, {"model": "planner"}, result(-1.253858544517839)),
    )
    found = duplicate_options(plan, garden)
    assert [(d.option_id, d.kept_option_id, d.kept_origin) for d in found] == [
        ("adv", "planner", "planner")
    ]


def test_distinct_results_are_not_duplicates() -> None:
    plan = model_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0)),
        universe(plan, {"model": "adv"}, result(-1.2)),
        universe(plan, {"model": "planner"}, result(-1.3)),
    )
    assert duplicate_options(plan, garden) == []


def test_baseline_equal_options_stay_noops_not_duplicates() -> None:
    plan = model_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0)),
        universe(plan, {"model": "adv"}, result(1.0)),
        universe(plan, {"model": "planner"}, result(1.0)),
    )
    assert duplicate_options(plan, garden) == []
    assert len(excluded_options(plan, garden)) == 2


def test_the_flip_is_attributed_to_the_planner_option_and_the_report_says_so() -> None:
    plan = model_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0)),
        universe(plan, {"model": "adv"}, result(-0.5, p=0.9)),
        universe(plan, {"model": "planner"}, result(-0.5, p=0.9)),
    )
    flip = minimal_flip(plan, garden)
    assert flip is not None and flip.changes[0].to_option == "planner"
    report = build_report(plan, garden, flip)
    assert [d.option_id for d in report.duplicate_options] == ["adv"]
    joined = " ".join(report.caveats)
    assert "adv adv" in joined and "label planner" in joined
    assert "one finding, not two" in joined


def test_a_step_whose_alternatives_are_all_noops_is_named_as_without_effect() -> None:
    plan = plan_of(
        step_of("cov", "feature", option("c0", True), option("c1")),
        step_of("model", "model", option("m", True), option("n")),
    )
    plan.step("cov").title = "Covariate set"
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0)),
        universe(plan, {"cov": "c1"}, result(1.0)),
        universe(plan, {"model": "n"}, result(0.7)),
    )
    report = build_report(plan, garden, None)
    assert any(
        "covariate decision 'Covariate set' had no effect on the model" in c for c in report.caveats
    )


def test_same_estimate_and_verdict_with_a_different_interval_is_a_duplicate() -> None:
    plan = model_plan()
    base = universe(plan, {}, result(1.0))
    planner = universe(plan, {"model": "planner"}, result(-0.5, half=0.2, p=0.011))
    robust = universe(plan, {"model": "adv"}, result(-0.5, half=0.21, p=0.0126))
    garden = garden_of(plan, base, planner, robust)
    found = duplicate_options(plan, garden)
    assert [(d.option_id, d.kept_option_id) for d in found] == [("adv", "planner")]
    assert "different standard error" in found[0].reason
    flip = minimal_flip(plan, garden)
    assert flip is not None and flip.changes[0].to_option == "planner"


def test_same_estimate_but_different_n_or_verdict_is_not_a_duplicate() -> None:
    plan = model_plan()
    base = universe(plan, {}, result(1.0))
    planner = universe(plan, {"model": "planner"}, result(-0.5, p=0.011))
    other_n = universe(plan, {"model": "adv"}, result(-0.5, p=0.011, n=90))
    assert duplicate_options(plan, garden_of(plan, base, planner, other_n)) == []
    wide = universe(plan, {"model": "adv"}, result(-0.5, half=5.0, p=0.9))
    wide.verdict = "NO CLEAR EVIDENCE"
    garden = garden_of(plan, base, planner, wide)
    assert duplicate_options(plan, garden) == []
