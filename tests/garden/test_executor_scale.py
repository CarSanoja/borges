from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisPlan, DecisionRule
from borges.garden.executor import GardenExecutor
from tests.garden import fakes
from tests.garden.fakes import FakeBackend, install_fake_harness, make_plan


@pytest.fixture(autouse=True)
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_harness(monkeypatch)


def _scaled_plan(scale: float) -> AnalysisPlan:
    plan = make_plan()
    rule = DecisionRule(metric="lift (percentage points)", threshold=5.0)
    return plan.model_copy(update={"result_scale": scale, "decision_rule": rule})


async def test_universe_results_and_verdict_use_the_scaled_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fakes, "BASE_ESTIMATE", 0.1)
    monkeypatch.setattr(fakes, "HALF_WIDTH", 0.02)
    monkeypatch.setattr(fakes, "EFFECTS", {})
    plan = _scaled_plan(100.0)
    executor = GardenExecutor(FakeBackend(plan), plan, b"d", emit=None)
    await executor.setup()
    universe = await executor.run_universe(plan.default_choices(), "baseline")
    assert universe.result is not None
    assert universe.result.estimate == pytest.approx(10.0)
    assert universe.result.ci_low == pytest.approx(8.0)
    assert universe.result.ci_high == pytest.approx(12.0)
    assert universe.result.p_value == fakes.P_VALUE and universe.result.n == 100
    assert universe.verdict == "SHIP"


async def test_unscaled_plan_keeps_raw_values_and_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fakes, "BASE_ESTIMATE", 0.1)
    monkeypatch.setattr(fakes, "HALF_WIDTH", 0.02)
    monkeypatch.setattr(fakes, "EFFECTS", {})
    plan = _scaled_plan(1.0)
    executor = GardenExecutor(FakeBackend(plan), plan, b"d", emit=None)
    await executor.setup()
    universe = await executor.run_universe(plan.default_choices(), "baseline")
    assert universe.result is not None and universe.result.estimate == pytest.approx(0.1)
    assert universe.verdict == "DON'T SHIP"


async def test_percentage_point_output_fails_the_universe_with_the_guard_message() -> None:
    plan = _scaled_plan(100.0)
    executor = GardenExecutor(FakeBackend(plan), plan, b"d", emit=None)
    await executor.setup()
    universe = await executor.run_universe(plan.default_choices(), "baseline")
    assert universe.status == "failed"
    assert universe.error is not None and "difference in proportions" in universe.error
