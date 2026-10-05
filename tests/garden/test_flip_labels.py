from __future__ import annotations

from borges.garden.estimand import estimand_changes
from borges.garden.search import contaminated_flip, minimal_flip
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, trace, universe

STOP = result(0.0, p=0.9)


def covariate_plan():
    return plan_of(
        step_of("rows", "filter", option("keep", True), option("drop")),
        step_of("model", "model", option("plain", True), option("adjusted")),
    )


def model_trace(*terms: str):
    return trace("model", terms=list(terms), deficient=False, rank=len(terms), columns=len(terms))


def test_options_that_change_the_covariates_are_labelled_estimand_changes() -> None:
    plan = covariate_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0), traces=[model_trace("x")]),
        universe(plan, {"model": "adjusted"}, STOP, traces=[model_trace("x", "age", "month")]),
        universe(plan, {"rows": "drop"}, result(0.9), traces=[model_trace("x")]),
    )
    found = estimand_changes(plan, garden)
    assert [(c.step_id, c.option_id) for c in found] == [("model", "adjusted")]
    assert "adds age, month" in found[0].detail and "estimand change" in found[0].detail


def test_a_flip_through_an_estimand_change_is_labelled() -> None:
    plan = covariate_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0), traces=[model_trace("x")]),
        universe(plan, {"model": "adjusted"}, STOP, traces=[model_trace("x", "age")]),
    )
    flip = minimal_flip(plan, garden)
    assert flip is not None and flip.estimand_change is not None
    assert "adds age" in flip.estimand_change


def test_a_plain_flip_wins_over_a_smaller_estimand_flip() -> None:
    plan = covariate_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0), traces=[model_trace("x")]),
        universe(plan, {"model": "adjusted"}, STOP, traces=[model_trace("x", "age")]),
        universe(plan, {"rows": "drop", "model": "plain"}, STOP, traces=[model_trace("x")]),
    )
    flip = minimal_flip(plan, garden)
    assert flip is not None and flip.estimand_change is None


def internal_plan():
    return plan_of(
        step_of(
            "traffic",
            "filter",
            option("exclude", True, code="df[~df.is_internal]", label="Exclude internal"),
            option("keep_all", label="Keep all sessions"),
        ),
        step_of("model", "model", option("m", True), option("n")),
        notes={"is_internal": "True for internal staff or test users, not genuine customers"},
    )


def test_reincluding_rows_the_notes_mark_invalid_is_a_contaminated_flip() -> None:
    plan = internal_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(0.4, p=0.4), traces=[trace("traffic", rows_after=900)]),
        universe(
            plan,
            {"traffic": "keep_all"},
            result(1.0),
            traces=[trace("traffic", rows_after=1000)],
        ),
    )
    assert minimal_flip(plan, garden) is None
    contaminated = contaminated_flip(plan, garden)
    assert contaminated is not None and contaminated.contaminated
    assert "re-includes 100 rows" in (contaminated.contamination_reason or "")
    assert "contaminated-analysis flip" in (contaminated.contamination_reason or "")


def test_excluding_more_rows_is_not_contamination() -> None:
    plan = internal_plan()
    plan.step("traffic").options[0].is_default = False
    plan.step("traffic").options[1].is_default = True
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0), traces=[trace("traffic", rows_after=1000)]),
        universe(plan, {"traffic": "exclude"}, STOP, traces=[trace("traffic", rows_after=900)]),
    )
    flip = minimal_flip(plan, garden)
    assert flip is not None and not flip.contaminated


def test_every_contaminated_flip_with_its_own_change_is_reported() -> None:
    from borges.garden.flips import contaminated_flips
    from borges.garden.influence import build_report

    plan = internal_plan()
    plan.step("traffic").options.append(option("bots_only", label="Exclude bots only"))
    rows = {"keep_all": (1000, 1.0), "bots_only": (950, 1.2)}
    garden = garden_of(
        plan,
        universe(plan, {}, result(0.4, p=0.4), traces=[trace("traffic", rows_after=900)]),
        *(
            universe(plan, {"traffic": o}, result(e), traces=[trace("traffic", rows_after=n)])
            for o, (n, e) in rows.items()
        ),
        universe(
            plan,
            {"traffic": "keep_all", "model": "n"},
            result(1.1),
            traces=[trace("traffic", rows_after=1000)],
        ),
    )
    found = contaminated_flips(plan, garden)
    assert sorted(f.changes[0].to_option for f in found) == ["bots_only", "keep_all"]
    report = build_report(plan, garden, None)
    assert len(report.contaminated_flips) == 2
    [note] = [c for c in report.caveats if "none is the headline" in c]
    assert note.startswith("2 flips were found") and "re-includes 50 rows" in note
