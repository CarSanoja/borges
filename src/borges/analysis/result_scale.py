from __future__ import annotations

import re

from borges.analysis.models import AnalysisResult, DecisionRule

PERCENTAGE_POINTS = re.compile(
    r"percentage[\s-]*points?|\bpps?\b|puntos?\s+porcentuales?", re.IGNORECASE
)
PROPORTION_WORDS = re.compile(
    r"proportion|probabilit|risk difference|rate difference|absolute (lift|difference|effect)"
    r"|proporci[oó]n|probabilidad|diferencia de (?:riesgos?|tasas)",
    re.IGNORECASE,
)
RATIO_WORDS = re.compile(
    r"ratio|relative risk|riesgo relativo|cociente"
    r"|raz[oó]n de (?:tasas|momios|odds|riesgos?|probabilidades|incidencias?|peligros?)",
    re.IGNORECASE,
)
SCALED_KEYS = ("estimate", "ci_low", "ci_high")
PERCENT_SCALE = 100.0


def detect_scale(metric: str) -> float:
    return PERCENT_SCALE if PERCENTAGE_POINTS.search(metric) else 1.0


def mentions_ratio(metric: str) -> bool:
    return RATIO_WORDS.search(metric) is not None


def is_proportion_rule(rule: DecisionRule) -> bool:
    return PROPORTION_WORDS.search(rule.metric) is not None and not mentions_ratio(rule.metric)


def reads_probability(metric: str) -> bool:
    words = PROPORTION_WORDS.search(metric) or PERCENTAGE_POINTS.search(metric)
    return words is not None and not mentions_ratio(metric)


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
                f"by 100; when the outcome itself is a percentage (0 to 100), divide the "
                f"estimate and both limits by 100"
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
