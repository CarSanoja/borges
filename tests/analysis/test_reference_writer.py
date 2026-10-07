from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisResult, StepTrace
from borges.analysis.reference_writer import propose_fixes, write_reference
from borges.llm.client import LLMError, Role
from tests.analysis.fakes import FakeLLM, make_plan

WHOLE = """
import statsmodels.formula.api as smf


def estimate(df, ctx):
    kept = df[df["group"] != "x"]
    fit = smf.ols("outcome ~ group", data=kept).fit()
    low, high = fit.conf_int().iloc[1]
    return {"estimate": float(fit.params.iloc[1]), "ci_low": float(low),
            "ci_high": float(high), "p_value": float(fit.pvalues.iloc[1]), "n": int(fit.nobs)}
"""
UNSAFE = "import os\n\n\ndef estimate(df, ctx):\n    return os.environ\n"
FILTER_FIX = "def apply(df, ctx):\n    return df[df['outcome'] > 0]\n"
RESULT = AnalysisResult(estimate=1.0, ci_low=0.5, ci_high=1.5, p_value=0.01, n=97)


def analysis_plan():
    plan = make_plan(with_code=True)
    plan.analysis = "keep groups other than x; OLS of outcome on group"
    return plan


async def test_a_whole_analysis_may_filter_rows_and_uses_the_second_model() -> None:
    llm = FakeLLM({"reference:1:0": {"code": WHOLE}})
    assert await write_reference(llm, analysis_plan(), 1) == WHOLE
    assert llm.calls[0].role == Role.REPAIRER
    assert '"attempt":1' in llm.calls[0].messages[1]["content"]


async def test_refused_code_is_shown_to_the_writer_then_fails() -> None:
    llm = FakeLLM({f"reference:2:{r}": {"code": UNSAFE} for r in range(3)})
    with pytest.raises(LLMError, match="refused"):
        await write_reference(llm, analysis_plan(), 2)
    assert len(llm.calls) == 3
    assert "the code was refused" in llm.calls[2].messages[1]["content"]


async def test_fixes_for_unknown_options_or_refused_code_are_dropped() -> None:
    plan = analysis_plan()
    fixes = [
        {"step_id": "d1", "option_id": "keep", "problem": "kept too many rows", "code": FILTER_FIX},
        {"step_id": "d1", "option_id": "nope", "problem": "p", "code": FILTER_FIX},
        {"step_id": "zz", "option_id": "keep", "problem": "p", "code": FILTER_FIX},
        {"step_id": "d1", "option_id": "trim", "problem": "p", "code": UNSAFE},
    ]
    llm = FakeLLM({"reference:fix:0": {"fixes": fixes}, "reference:fix:1": {"fixes": []}})
    trace = [StepTrace(step_id="d1", option_id="keep", rows_before=100, rows_after=100)]
    found = await propose_fixes(llm, plan, trace, RESULT, RESULT, WHOLE)
    assert [(f.step_id, f.option_id) for f in found] == [("d1", "keep")]
    sent = llm.calls[0].messages[1]["content"]
    assert '"rows_before_after_on_full_data":[100,100]' in sent
    assert '"reference_code"' in sent


async def test_a_refused_fix_goes_back_once_with_the_reason() -> None:
    plan = analysis_plan()
    first = [{"step_id": "d1", "option_id": "keep", "problem": "p", "code": UNSAFE}]
    second = [{"step_id": "d1", "option_id": "keep", "problem": "p", "code": FILTER_FIX}]
    llm = FakeLLM({"reference:fix:0": {"fixes": first}, "reference:fix:1": {"fixes": second}})
    found = await propose_fixes(llm, plan, [], RESULT, RESULT, WHOLE)
    assert [f.code for f in found] == [FILTER_FIX]
    retry = llm.calls[1].messages[-1]["content"]
    assert "were refused" in retry and "d1/keep" in retry and "os" in retry
