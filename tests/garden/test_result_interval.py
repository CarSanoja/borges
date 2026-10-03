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
