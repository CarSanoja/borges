from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisResult
from borges.garden.result_interval import interval_error
from tests.garden import fakes
from tests.garden.fakes import FakeBackend, install_fake_harness, make_plan


def result(**overrides: float) -> AnalysisResult:
    base = {"estimate": -0.1273, "ci_low": -0.15, "ci_high": -0.10, "p_value": 0.01, "n": 50}
    return AnalysisResult.model_validate({**base, **overrides})


def test_healthy_interval_passes() -> None:
    assert interval_error(result()) is None


def test_zero_width_interval_is_rejected() -> None:
    error = interval_error(result(ci_low=-0.1273, ci_high=-0.1273))
    assert error is not None and "zero width" in error and "-0.1273" in error


def test_near_zero_width_relative_to_estimate_is_rejected() -> None:
    error = interval_error(result(ci_low=-0.1273 - 1e-9, ci_high=-0.1273 + 1e-9))
    assert error is not None and "zero width" in error


def test_zero_width_at_zero_estimate_is_rejected() -> None:
    assert interval_error(result(estimate=0.0, ci_low=0.0, ci_high=0.0)) is not None


def test_narrow_but_real_interval_passes() -> None:
    assert interval_error(result(ci_low=-0.1274, ci_high=-0.1272)) is None


def test_non_finite_values_are_rejected() -> None:
    error = interval_error(result(ci_high=float("inf")))
    assert error is not None and "non-finite ci_high" in error
    assert interval_error(result(ci_low=float("nan"))) is not None


def test_interval_not_containing_the_estimate_is_rejected() -> None:
    error = interval_error(result(estimate=0.5))
    assert error is not None and "does not contain" in error


def test_inverted_interval_is_rejected() -> None:
    error = interval_error(result(ci_low=-0.1, ci_high=-0.2))
    assert error is not None and "inverted" in error


async def test_universe_with_zero_width_interval_fails_after_scaling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_harness(monkeypatch)
    monkeypatch.setattr(fakes, "BASE_ESTIMATE", -0.1273)
    monkeypatch.setattr(fakes, "HALF_WIDTH", 0.0)
    monkeypatch.setattr(fakes, "EFFECTS", {})
    plan = make_plan().model_copy(update={"result_scale": 100.0})
    from borges.garden.executor import GardenExecutor

    executor = GardenExecutor(FakeBackend(plan), plan, b"d", emit=None)
    await executor.setup()
    universe = await executor.run_universe(plan.default_choices(), "baseline")
    assert universe.status == "failed"
    assert universe.error is not None and "zero width" in universe.error


@pytest.mark.parametrize(
    ("estimate", "low", "high", "p"),
    [
        (-502.86, -1157.0, 155.31, 1.0),
        (-489.55, -1127.77, 168.49, 1.0),
        (2.0, 1.0, 3.0, 0.9),
        (0.1, -2.0, 2.2, 1e-9),
    ],
)
def test_a_p_value_the_interval_cannot_give_is_rejected(
    estimate: float, low: float, high: float, p: float
) -> None:
    problem = interval_error(result(estimate=estimate, ci_low=low, ci_high=high, p_value=p))
    assert problem is not None and "come from different tests" in problem


@pytest.mark.parametrize(
    ("estimate", "low", "high", "p"),
    [
        (-502.86, -1197.4, 191.69, 0.156),
        (1.35, 1.1, 1.66, 0.004),
        (-1.15, -21.57, 0.186, 0.106),
        (12.0, 10.0, 14.0, 0.0),
        (0.02, -0.5, 0.54, 0.94),
    ],
)
def test_p_values_that_match_their_interval_pass(
    estimate: float, low: float, high: float, p: float
) -> None:
    assert interval_error(result(estimate=estimate, ci_low=low, ci_high=high, p_value=p)) is None
