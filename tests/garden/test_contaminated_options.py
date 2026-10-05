from __future__ import annotations

from borges.garden.contaminated_options import contaminated_notes, contaminated_options
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, trace, universe


def filter_plan():
    return plan_of(
        step_of(
            "rows",
            "filter",
            option("clean", True, label="Exclude internal and short sessions"),
            option("all", label="Keep all records"),
            option("internal", label="Exclude internal only"),
        ),
        step_of("model", "model", option("ols", True), option("logit")),
    )


def test_an_option_that_re_includes_invalid_rows_is_excluded_with_a_note() -> None:
    plan = filter_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(-0.13, p=0.46), traces=[trace("rows", rows_after=29186)]),
        universe(plan, {"rows": "all"}, result(0.53), traces=[trace("rows", rows_after=29926)]),
        universe(
            plan,
            {"rows": "internal"},
            result(-0.14, p=0.4),
            traces=[trace("rows", rows_after=29000)],
        ),
    )
    found = contaminated_options(plan, garden)
    assert [(o.step_id, o.option_id) for o in found] == [("rows", "all")]
    assert "re-includes 740 rows" in found[0].reason and "internal" in found[0].reason
    assert "excluded from the robustness share" in contaminated_notes(found)[0]


def test_a_baseline_that_keeps_every_row_excludes_nothing() -> None:
    plan = plan_of(
        step_of("rows", "filter", option("all", True, label="Keep all"), option("clean")),
        step_of("model", "model", option("ols", True)),
    )
    garden = garden_of(
        plan,
        universe(plan, {}, result(0.53), traces=[trace("rows", rows_after=29926)]),
        universe(plan, {"rows": "clean"}, result(-0.1), traces=[trace("rows", rows_after=29186)]),
    )
    assert contaminated_options(plan, garden) == []
