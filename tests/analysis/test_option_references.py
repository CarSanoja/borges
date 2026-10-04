from __future__ import annotations

from borges.analysis.models import Option
from borges.analysis.option_references import expand_option, normalise_plan
from tests.analysis.fakes import make_plan


def _model_step(plan):
    return next(s for s in plan.steps if s.kind == "model")


def _opt(option_id: str, label: str, spec: str) -> Option:
    return Option(id=option_id, label=label, rationale="r", spec=spec)


def test_reference_by_id_appends_referenced_spec_once() -> None:
    plan = make_plan()
    step = _model_step(plan)
    step.options = [
        _opt("opt_pois_robust", "Robust Poisson", "Poisson GLM with offset log(n), HC1"),
        _opt("opt_pois_cluster", "Clustered", "Same as opt_pois_robust but cluster by referee"),
    ]
    normalise_plan(plan)
    normalise_plan(plan)
    spec = step.options[1].spec
    assert spec.count("(opt_pois_robust:") == 1
    assert "Poisson GLM with offset log(n), HC1" in spec
    assert step.options[0].spec == "Poisson GLM with offset log(n), HC1"


def test_reference_by_exact_label_case_insensitive() -> None:
    plan = make_plan()
    step = _model_step(plan)
    step.options = [
        _opt("a", "OLS basic", "OLS of y on x"),
        _opt("b", "OLS gdp", "same as ols basic but add gdp"),
    ]
    normalise_plan(plan)
    assert "(a: OLS of y on x)" in step.options[1].spec


def test_mutual_references_do_not_recurse() -> None:
    plan = make_plan()
    step = _model_step(plan)
    step.options = [
        _opt("a_opt", "A", "like b_opt plus x"),
        _opt("b_opt", "B", "like a_opt plus y"),
    ]
    normalise_plan(plan)
    assert step.options[0].spec == "like b_opt plus x (b_opt: like a_opt plus y)"
    assert step.options[1].spec == "like a_opt plus y (a_opt: like b_opt plus x)"


def test_word_boundary_and_no_reference_unchanged() -> None:
    plan = make_plan()
    step = _model_step(plan)
    step.options = [_opt("ols", "OLS plain", "OLS"), _opt("ols_gdp", "gdp", "ols_gdp_extra model")]
    normalise_plan(plan)
    assert step.options[1].spec == "ols_gdp_extra model"


def test_expand_option_for_proposal() -> None:
    plan = make_plan()
    step = _model_step(plan)
    base = step.options[0]
    proposal = _opt("new_one", "New", f"Same as {base.id} but with robust errors")
    expanded = expand_option(plan, step, proposal)
    assert f"({base.id}: {base.spec}" in expanded.spec
