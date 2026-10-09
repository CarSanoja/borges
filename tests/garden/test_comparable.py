from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.garden.comparable import comparable, other_scale, scale_caveats
from borges.garden.estimand import estimand_detail
from borges.garden.influence import decision_influence
from borges.garden.robustness import counted_universes
from tests.garden.synthetic import garden_of, option, plan_of, step_of, trace, universe

PLAN = plan_of(
    step_of("m", "model", option("pois", True), option("zip"), option("nb")),
)


def counts(estimate: float, **extra: float) -> AnalysisResult:
    return AnalysisResult(
        estimate=estimate,
        ci_low=estimate - 0.03,
        ci_high=estimate + 0.03,
        p_value=0.01,
        n=100,
        extra=extra,
    )


def garden():
    return garden_of(
        PLAN,
        universe(
            PLAN,
            {},
            counts(-0.188, coefficient=-0.068),
            traces=[trace("m", model="GLM", family="Poisson", link="Log", outcome="visits")],
        ),
        universe(
            PLAN,
            {"m": "zip"},
            counts(-0.0315),
            traces=[trace("m", model="ZeroInflatedPoisson", outcome="visits")],
        ),
        universe(
            PLAN,
            {"m": "nb"},
            counts(-0.174, coefficient=-0.063),
            traces=[trace("m", model="GLM", family="NegativeBinomial", link="Log")],
        ),
    )


def test_a_zero_inflated_raw_coefficient_beside_a_marginal_effect_is_another_scale() -> None:
    found = garden()
    baseline, zero_inflated, negbin = found.universes.values()
    assert other_scale(baseline, zero_inflated) is not None
    assert estimand_detail(baseline, zero_inflated) is not None
    assert comparable(baseline, negbin)
    assert comparable(baseline, baseline)


def test_the_odd_one_out_is_left_out_of_the_largest_shift_and_the_robustness_pool() -> None:
    found = garden()
    [row] = decision_influence(PLAN, found)
    assert row.max_abs_delta == abs(-0.174 + 0.188)
    assert [u.choices["m"] for u in counted_universes(found, [])] == ["pois", "nb"]


def test_the_caveat_names_the_count_and_the_range_of_the_apart_universes() -> None:
    [caveat] = scale_caveats(garden())
    assert caveat.startswith("1 universes report an estimate on another scale")
    assert "-0.0315" in caveat


def test_zero_inflated_models_beside_each_other_are_comparable() -> None:
    plan = plan_of(step_of("m", "model", option("zip", True), option("zip2")))
    zero_inflated = [trace("m", model="ZeroInflatedPoisson")]
    found = garden_of(
        plan,
        universe(plan, {}, counts(-0.03), traces=zero_inflated),
        universe(plan, {"m": "zip2"}, counts(-0.04), traces=zero_inflated),
    )
    assert scale_caveats(found) == []
