from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.analysis.code_guard_coefficient import positional_estimate_violations
from borges.analysis.coder_checks import option_violations
from tests.analysis.fakes import make_plan

INCIDENT = """\
def estimate(df, ctx):
    num_cov = ctx.get("covariates", [])
    res = sm.OLS(y, X).fit(cov_type="HC2")
    params = res.params
    est = float(params.iloc[-1] if len(num_cov) > 0 else params["interaction"])
    ci = res.conf_int(alpha=0.05)
    low = float(ci.iloc[-1, 0] if len(num_cov) > 0 else ci.loc["interaction", 0])
    return {"estimate": est, "ci_low": low}
"""


def test_the_fertility_incident_is_flagged_on_both_reads() -> None:
    found = positional_estimate_violations(INCIDENT)
    assert [f.split(":")[0] for f in found] == ["line 5", "line 7"]
    assert "params.iloc[-1]" in found[0] and "by the term's name" in found[0]


@pytest.mark.parametrize(
    "line",
    [
        "est = res.params[3]",
        "p = res.pvalues.iloc[2]",
        "se = res.bse[-1]",
        "low = res.conf_int().iloc[-1, 0]",
        "low = res.conf_int(alpha=0.05).iloc[3]",
        "est = res.params.values[1]",
        "coeffs = res.params\nest = coeffs[3]",
        "ci = res.conf_int()\nlow = ci.iloc[3, 0]",
        "i = names.index('treated')\ni = 2\nest = res.params.iloc[i]",
    ],
)
def test_reading_a_term_by_position_is_flagged(line: str) -> None:
    assert len(positional_estimate_violations(line + "\n")) == 1


@pytest.mark.parametrize(
    "line",
    [
        "est = res.params['beauty']",
        "low, high = res.conf_int().loc['beauty']",
        "ci = res.conf_int().loc['beauty']\nlow = ci[0]\nhigh = ci.iloc[1]",
        "low = res.conf_int()[0]['beauty']",
        "low = res.conf_int().iloc[:, 0]['beauty']",
        "first = df.iloc[0]\nvalue = rows[3]",
        "i = fit.model.exog_names.index('treated')\nci = fit.conf_int()\nlow = ci.iloc[i, 0]",
        "est = res.params.iloc[res.params.index.get_loc('treated')]",
    ],
)
def test_reading_a_term_by_name_passes(line: str) -> None:
    assert positional_estimate_violations(line + "\n") == []


def test_every_shipped_fixture_reads_the_estimate_by_name() -> None:
    codes = []
    for path in Path("cases").glob("*/fixtures/coder__*.json"):
        code = json.loads(path.read_text()).get("parsed", {}).get("code", "")
        if "def estimate" in code:
            codes.append(code)
    assert codes and all(positional_estimate_violations(c) == [] for c in codes)


def test_the_model_step_checks_include_it() -> None:
    plan = make_plan()
    step = plan.step("m1")
    found = option_violations(INCIDENT, plan, step, step.options[0])
    assert any("by position" in f for f in found)
