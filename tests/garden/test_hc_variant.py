from __future__ import annotations

from borges.analysis.models import StepTrace
from borges.garden.hc_variant import hc_variant_caveats
from borges.garden.models import Garden, Universe


def universe(uid: str, model: str, cov_type: str | None) -> Universe:
    design = {"model": model, "cov_type": cov_type}
    trace = StepTrace(step_id="m", option_id="o", rows_before=9, rows_after=9, design=design)
    return Universe(id=uid, choices={}, kind="single", traces=[trace])


def test_hc3_on_a_logit_is_declared_as_hc0() -> None:
    garden = Garden()
    garden.add(universe("u1", "Logit", "HC3"))
    garden.add(universe("u2", "GLM", "HC1"))
    garden.add(universe("u3", "Logit", "cluster"))
    [caveat] = hc_variant_caveats(garden)
    assert caveat.startswith("In 2 universes the model asked statsmodels for HC1 or HC3")
    assert "GLM or Logit fit" in caveat and "are HC0" in caveat


def test_hc3_on_ols_is_computed_and_needs_no_caveat() -> None:
    garden = Garden()
    garden.add(universe("u1", "OLS", "HC3"))
    garden.add(universe("u2", "Logit", "HC0"))
    assert hc_variant_caveats(garden) == []
