from __future__ import annotations

import pytest
import statsmodels.api as sm

from borges.analysis.model_spec.render import render_code
from borges.analysis.models import Comparator, DecisionRule
from tests.analysis.model_spec.data import make_spec, synthetic
from tests.analysis.model_spec.test_validate_exposure import AVAILABLE, PROFILE

DEATHS = DecisionRule(metric="additional deaths", comparator=Comparator.GT, threshold=0.0)


def test_a_poisson_marginal_effect_is_the_one_statsmodels_computes() -> None:
    frame = synthetic().dropna()
    namespace: dict = {}
    spec = make_spec("poisson", exposure="m", covariates=["x", "a"], report="marginal_effect")
    exec(render_code(spec), namespace)
    got = namespace["estimate"](frame, {})
    exog = sm.add_constant(frame[["m", "x", "a"]].astype(float), has_constant="add")
    effect = sm.Poisson(frame["y_count"], exog).fit(disp=0).get_margeff(at="overall")
    row = effect.summary_frame().loc["m"]
    assert got["estimate"] == pytest.approx(float(row["dy/dx"]), rel=1e-6)
    assert got["ci_low"] == pytest.approx(float(row["Conf. Int. Low"]), rel=1e-6)
    assert got["ci_high"] == pytest.approx(float(row["Cont. Int. Hi."]), rel=1e-6)
    assert got["p_value"] == pytest.approx(float(row["Pr(>|z|)"]), rel=1e-6)


def test_a_count_model_for_a_difference_rule_reports_additional_events() -> None:
    from borges.analysis.model_spec.validate import validate_spec

    ratio = make_spec("poisson", outcome="m", exposure="wide", report="rate_ratio")
    margin = make_spec("poisson", outcome="m", exposure="wide", report="marginal_effect")
    [problem] = validate_spec(ratio, AVAILABLE, PROFILE, DEATHS)
    assert "use report marginal_effect" in problem
    assert validate_spec(margin, AVAILABLE, PROFILE, DEATHS) == []
