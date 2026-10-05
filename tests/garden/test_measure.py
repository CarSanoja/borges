from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.garden.estimand import estimand_detail
from borges.garden.measure import measure_caveats, reported_measure
from tests.garden.synthetic import garden_of, option, plan_of, step_of, trace, universe

PLAN = plan_of(
    step_of("m", "model", option("logit", True), option("pois", label="Poisson"), option("cl"))
)


def ratio(estimate: float) -> AnalysisResult:
    return AnalysisResult(
        estimate=estimate, ci_low=estimate / 1.1, ci_high=estimate * 1.1, p_value=0.01, n=100
    )


def garden():
    return garden_of(
        PLAN,
        universe(PLAN, {}, ratio(0.884), traces=[trace("m", model="Logit")]),
        universe(
            PLAN, {"m": "pois"}, ratio(0.896), traces=[trace("m", model="GLM", family="Poisson")]
        ),
        universe(PLAN, {"m": "cl"}, ratio(0.881), traces=[trace("m", model="Logit")]),
    )


def test_a_rate_ratio_beside_an_odds_ratio_is_named() -> None:
    found = garden()
    assert [reported_measure(u) for u in found.universes.values()] == [
        "odds ratio",
        "rate ratio",
        "odds ratio",
    ]
    [caveat] = measure_caveats(PLAN, found)
    assert caveat.startswith(
        "The option 'Poisson' (m) reports a rate ratio where the original analysis reports an "
        "odds ratio"
    )


def test_a_flip_to_another_measure_is_an_estimand_change() -> None:
    found = garden()
    baseline, pois, _ = found.universes.values()
    detail = estimand_detail(baseline, pois)
    assert detail is not None and detail.startswith("reports a rate ratio where")
    assert reported_measure(universe(PLAN, {}, ratio(0.9))) is None


def test_a_rule_stated_as_an_odds_ratio_over_a_rate_ratio_is_named() -> None:
    from borges.analysis.models import DecisionRule
    from borges.garden.measure import rule_measure_caveats

    stated = PLAN.model_copy(
        update={"decision_rule": DecisionRule(metric="odds ratio of a red card per game")}
    )
    pois = garden_of(
        stated,
        universe(stated, {}, ratio(1.14), traces=[trace("m", model="GLM", family="Poisson")]),
    )
    [caveat] = rule_measure_caveats(stated, pois)
    assert caveat.startswith("The decision rule is stated as an odds ratio, but the original")
    assert rule_measure_caveats(PLAN, garden()) == []
