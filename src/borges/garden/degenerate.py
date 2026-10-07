"""A fit that cannot be estimated on the data it was given.

fertility_vote on 7 October: one window option left a cell of the logistic model with every woman
voting the same way. The fit returned -36.6 with a 95% interval of about ±43,000, p 0.999, and the
run reported it as the smallest flip. Such an interval says the model has no answer, not that the
effect is unclear. Rescaling an outcome widens the interval and the estimate together; separation
or collinearity widens the interval alone. So a result is set aside when its interval is over 100
times wider than the baseline's and also over 100 times wider relative to its own estimate.
"""

from __future__ import annotations

from borges.analysis.models import AnalysisResult

DEGENERATE_REASON = "not estimable"
RATIO = 100.0
TINY = 1e-12


def _half_width(result: AnalysisResult) -> float:
    return (result.ci_high - result.ci_low) / 2


def is_degenerate(baseline: AnalysisResult, result: AnalysisResult) -> bool:
    base, wide = _half_width(baseline), _half_width(result)
    if base <= 0 or wide <= RATIO * base or abs(baseline.estimate) < TINY:
        return False
    relative_base = base / abs(baseline.estimate)
    relative = wide / max(abs(result.estimate), TINY)
    return relative > RATIO * relative_base


def degenerate_message(baseline: AnalysisResult, result: AnalysisResult) -> str:
    ratio = _half_width(result) / _half_width(baseline)
    return (
        f"{DEGENERATE_REASON}: the 95% interval ({result.ci_low:.6g} to {result.ci_high:.6g}) is "
        f"{ratio:,.0f} times wider than the baseline's, the mark of a model that cannot be fitted "
        "on this data (separation or collinearity), so the result says nothing about the question"
    )
