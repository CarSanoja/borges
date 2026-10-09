from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.garden.estimand import estimand_detail
from borges.garden.measure import (
    location_measure,
    measure_caveats,
    reported_measure,
    shared_measure,
)
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


def test_a_measure_is_shared_only_when_every_universe_reports_it() -> None:
    counts = garden_of(
        PLAN,
        universe(PLAN, {}, ratio(1.15), traces=[trace("m", model="GLM", family="Poisson")]),
        universe(
            PLAN,
            {"m": "pois"},
            ratio(1.16),
            traces=[trace("m", model="GLM", family="NegativeBinomial")],
        ),
    )
    assert shared_measure(counts) == "rate ratio"
    assert shared_measure(garden()) is None


def test_a_binomial_glm_is_read_with_its_link() -> None:
    def measured(**design: object) -> str | None:
        return reported_measure(universe(PLAN, {}, ratio(0.88), traces=[trace("m", **design)]))

    assert measured(model="GLM", family="Binomial", link="Logit") == "odds ratio"
    assert measured(model="GLM", family="Binomial", link="CLogLog") == (
        "hazard ratio (complementary log-log link)"
    )
    assert measured(model="GLM", family="Binomial", link="Log") == "risk ratio"
    assert measured(model="GLM", family="Binomial", link="Probit") is None
    assert measured(model="GLM", family="Binomial") == "odds ratio"


def test_a_median_regression_beside_a_mean_is_an_estimand_change() -> None:
    plan = plan_of(step_of("m", "model", option("ols", True), option("qr", label="Median")))
    gap = AnalysisResult(estimate=-503.0, ci_low=-1197.0, ci_high=192.0, p_value=0.16, n=1500)
    median = AnalysisResult(estimate=-1230.0, ci_low=-1976.0, ci_high=-484.0, p_value=0.001, n=1500)
    found = garden_of(
        plan,
        universe(plan, {}, gap, traces=[trace("m", model="OLS")]),
        universe(plan, {"m": "qr"}, median, traces=[trace("m", model="QuantReg")]),
    )
    baseline, quantile = found.universes.values()
    assert location_measure(baseline) == "conditional mean"
    detail = estimand_detail(baseline, quantile)
    assert detail is not None and detail.startswith(
        "estimates a conditional quantile (the median unless another quantile is set) where the "
        "original analysis estimates a conditional mean"
    )
    assert estimand_detail(baseline, baseline) is None
