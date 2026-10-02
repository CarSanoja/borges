from __future__ import annotations

import re

from borges.analysis.models import AnalysisResult

PERCENTAGE_POINTS = re.compile(r"percentage[\s-]*points?|\bpps?\b", re.IGNORECASE)
SCALED_KEYS = ("estimate", "ci_low", "ci_high")
PERCENT_SCALE = 100.0


def detect_scale(metric: str) -> float:
    return PERCENT_SCALE if PERCENTAGE_POINTS.search(metric) else 1.0


def scale_error(raw: dict[str, object] | AnalysisResult, scale: float) -> str | None:
    if scale == 1.0:
        return None
    values = raw.model_dump() if isinstance(raw, AnalysisResult) else raw
    for key in SCALED_KEYS:
        value = values.get(key)
        if isinstance(value, int | float) and abs(value) > 1.0:
            return (
                f"the metric is in percentage points and Borges converts units itself, so "
                f"{key} must be returned as a difference in proportions (between -1 and 1), "
                f"not in percentage points; got {key}={value:.6g}. Remove any multiplication "
                f"by 100 and return the difference in proportions"
            )
    return None


def apply_scale(result: AnalysisResult, scale: float) -> AnalysisResult:
    if scale == 1.0:
        return result
    return result.model_copy(update={key: getattr(result, key) * scale for key in SCALED_KEYS})


def convert(result: AnalysisResult, scale: float) -> tuple[AnalysisResult | None, str | None]:
    error = scale_error(result, scale)
    if error is not None:
        return None, error
    return apply_scale(result, scale), None
