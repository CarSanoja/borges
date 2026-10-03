from __future__ import annotations

from borges.analysis.models import AnalysisResult

SIGNIFICANT_DIGITS = 6

ResultKey = tuple[float, float, float, int]


def result_key(result: AnalysisResult) -> ResultKey:
    def rounded(value: float) -> float:
        return float(f"{value:.{SIGNIFICANT_DIGITS - 1}e}")

    return (rounded(result.estimate), rounded(result.ci_low), rounded(result.ci_high), result.n)
