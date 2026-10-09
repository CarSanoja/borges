"""A verdict past a threshold that the interval does not clear.

The decision rule is positive when the estimate is past the threshold and its p-value is below
alpha, and the p-value of a model's coefficient tests no effect: 0 for a difference, 1 for a
ratio. A K-12 question asked whether each weekly hour of tutoring adds at least half a point; an
estimate of 0.68 with p 1e-9 is past 0.5 and significant, but its interval [0.46, 0.90] includes
0.5, so the data show an effect, not that it is at least half a point. When the threshold is not
the no-effect value and the interval of a positive verdict reaches it, the report says so.
"""

from __future__ import annotations

from borges.analysis.models import AnalysisResult, DecisionRule
from borges.analysis.result_scale import mentions_ratio


def threshold_interval_caveats(rule: DecisionRule, result: AnalysisResult) -> list[str]:
    null = 1.0 if mentions_ratio(rule.metric) else 0.0
    if rule.threshold == null or not rule.is_positive(result):
        return []
    if not result.ci_low <= rule.threshold <= result.ci_high:
        return []
    return [
        f"The verdict compares the estimate {result.estimate:.4g} with {rule.threshold:g}, and "
        f"its p-value tests no effect ({null:g}); the interval [{result.ci_low:.4g}, "
        f"{result.ci_high:.4g}] includes {rule.threshold:g}, so the data show an effect but not "
        f"that it is past {rule.threshold:g}."
    ]
