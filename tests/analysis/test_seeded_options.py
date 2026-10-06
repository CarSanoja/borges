from __future__ import annotations

from borges.analysis.models import RepeatedUnit
from borges.analysis.seeded_options import cluster_option_id, seed_cluster_options
from tests.analysis.fakes import make_plan

LOGIT = (
    "import statsmodels.api as sm\n\n\ndef estimate(df, ctx):\n"
    '    fit = sm.Logit(df["y"], df[["x"]]).fit(disp=0, cov_type="HC3")\n'
    '    return {"estimate": 1.0}\n'
)
UNITS = [
    RepeatedUnit(name="playerShort", n_units=1585, rows_per_unit=78.6),
    RepeatedUnit(name="refNum", n_units=3147, rows_per_unit=46.4),
]


def plan_with_units(code: str | None = LOGIT, units: list[RepeatedUnit] | None = None):
    plan = make_plan(with_code=True)
    plan.step("m1").option("ols").code = code
    plan.step("m1").option("ols").spec = "Logistic regression of y on x, HC3 errors."
    plan.dataset = plan.dataset.model_copy(
        update={"repeated_units": UNITS if units is None else units}
    )
    return plan


def test_each_repeated_unit_gets_a_pinned_cluster_option_whatever_the_planner_proposed() -> None:
    plan = plan_with_units()
    before = [o.id for o in plan.step("m1").options]
    added = seed_cluster_options(plan)
    assert added == ["cluster_playershort", "cluster_refnum"]
    options = {o.id: o for o in plan.step("m1").options}
    assert list(options)[: len(before)] == before
    player = options["cluster_playershort"]
    assert player.origin == "pinned" and not player.is_default
    assert (
        player.cluster_by == "playerShort" and player.label == "Cluster the errors by playerShort"
    )
    assert "cluster-robust by playerShort" in player.spec and "Logistic regression" in player.spec
    assert player.code == LOGIT
    assert options["cluster_refnum"].cluster_by == "refNum"
    assert plan.step("m1").default.id == "ols" and plan.step("m1").default.cluster_by is None


def test_seeding_twice_adds_nothing() -> None:
    plan = plan_with_units()
    seed_cluster_options(plan)
    assert seed_cluster_options(plan) == []
    assert len(plan.step("m1").options) == 4


def test_no_repeated_units_seeds_nothing() -> None:
    plan = plan_with_units(units=[])
    assert seed_cluster_options(plan) == []
    assert [o.id for o in plan.step("m1").options] == ["ols", "welch"]


def test_a_default_model_that_cannot_cluster_or_already_clusters_seeds_nothing() -> None:
    quantile = LOGIT.replace(
        'sm.Logit(df["y"], df[["x"]]).fit(disp=0, cov_type="HC3")', "sm.QuantReg(y, x).fit()"
    )
    gee = LOGIT.replace("sm.Logit", "sm.GEE")
    clustered = LOGIT.replace('"HC3"', '"cluster", cov_kwds={"groups": g}')
    for code in (quantile, gee, clustered, None):
        assert seed_cluster_options(plan_with_units(code)) == []


def test_a_unit_named_in_the_metric_is_the_exposure_not_a_unit() -> None:
    plan = plan_with_units()
    plan.decision_rule = plan.decision_rule.model_copy(update={"metric": "effect of refNum"})
    assert seed_cluster_options(plan) == ["cluster_playershort"]


def test_the_option_id_is_a_slug_of_the_unit() -> None:
    assert cluster_option_id("User ID") == "cluster_user_id"
