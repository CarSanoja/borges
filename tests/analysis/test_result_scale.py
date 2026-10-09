from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.analysis.result_scale import (
    apply_scale,
    convert,
    detect_scale,
    reads_probability,
    scale_error,
)
from tests.analysis.fakes import make_plan


def _result(estimate: float, low: float, high: float) -> AnalysisResult:
    return AnalysisResult(estimate=estimate, ci_low=low, ci_high=high, p_value=0.04, n=50)


@pytest.mark.parametrize(
    ("metric", "scale"),
    [
        ("conversion lift, treatment minus control (percentage points)", 100.0),
        ("difference in Percentage Point terms", 100.0),
        ("lift in pp", 100.0),
        ("lift (pp)", 100.0),
        ("standardised coefficient of religiosity on well-being", 1.0),
        ("odds ratio of a red card per game", 1.0),
        ("approach to the topic", 1.0),
    ],
)
def test_scale_is_read_from_the_metric_text(metric: str, scale: float) -> None:
    assert detect_scale(metric) == scale


def test_apply_scale_multiplies_estimate_and_bounds_only() -> None:
    scaled = apply_scale(_result(-0.0014, -0.01, 0.0072), 100.0)
    assert scaled.estimate == pytest.approx(-0.14)
    assert scaled.ci_low == pytest.approx(-1.0)
    assert scaled.ci_high == pytest.approx(0.72)
    assert scaled.p_value == 0.04 and scaled.n == 50


def test_scale_one_returns_the_same_result() -> None:
    result = _result(12.78, 10.0, 15.0)
    assert apply_scale(result, 1.0) is result
    assert scale_error(result, 1.0) is None


@pytest.mark.parametrize("values", [(1.4, 0.2, 2.6), (0.5, -1.3, 0.9), (0.0, -0.1, 3.0)])
def test_guard_rejects_percentage_point_values_for_scale_100(
    values: tuple[float, float, float],
) -> None:
    error = scale_error(_result(*values), 100.0)
    assert error is not None
    assert "difference in proportions" in error and "percentage points" in error
    assert "when the outcome itself is a percentage (0 to 100), divide the estimate" in error
    scaled, same_error = convert(_result(*values), 100.0)
    assert scaled is None and same_error == error


def test_guard_accepts_proportions_and_convert_scales_them() -> None:
    scaled, error = convert(_result(0.0127, 0.001, 0.0244), 100.0)
    assert error is None and scaled is not None
    assert scaled.estimate == pytest.approx(1.27)


def test_plan_without_the_field_defaults_to_scale_one() -> None:
    data = make_plan().model_dump(mode="json")
    data.pop("result_scale")
    assert AnalysisPlan.model_validate(data).result_scale == 1.0


@pytest.mark.parametrize(
    ("metric", "scale", "probability"),
    [
        ("efecto en la probabilidad de fraude, en puntos porcentuales", 100.0, True),
        ("diferencia en la proporción de aprobados", 1.0, True),
        ("diferencia de riesgos de impago", 1.0, True),
        ("razón de momios de impago", 1.0, False),
        ("cambio medio del puntaje de lectura", 1.0, False),
    ],
)
def test_spanish_metrics_are_read_on_their_scale(
    metric: str, scale: float, probability: bool
) -> None:
    assert detect_scale(metric) == scale
    assert reads_probability(metric) is probability
