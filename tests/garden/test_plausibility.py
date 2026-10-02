from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisResult
from borges.garden.executor import GardenExecutor
from borges.garden.influence import build_report, robustness
from borges.garden.plausibility import is_implausible
from tests.garden import fakes
from tests.garden.fakes import FakeBackend, install_fake_harness, make_plan


def res(estimate: float, low: float, high: float) -> AnalysisResult:
    return AnalysisResult(estimate=estimate, ci_low=low, ci_high=high, p_value=0.01, n=100)


MARP = res(0.0434, 0.025, 0.062)


def test_marp_norms_bayesian_garbage_is_implausible() -> None:
    assert is_implausible(MARP, res(-398439.37, -930079.0, 133200.0))


@pytest.mark.parametrize(
    "result",
    [
        res(0.15, 0.1, 0.2),
        res(-0.02, -0.06, 0.02),
        res(0.0, -0.04, 0.04),
        res(4.0, 1.0, 7.0),
        res(-3.0, -5.0, -1.0),
    ],
)
def test_ordinary_alternatives_are_plausible(result: AnalysisResult) -> None:
    assert not is_implausible(MARP, result)


def test_odds_ratios_around_one_are_plausible() -> None:
    baseline = res(0.92, 0.88, 0.96)
    assert not is_implausible(baseline, res(1.1, 0.9, 1.3))
    assert not is_implausible(baseline, res(0.5, 0.3, 0.8))


def test_non_finite_estimate_is_implausible() -> None:
    assert is_implausible(MARP, res(float("inf"), 0.0, 1.0))


async def test_implausible_universe_fails_and_is_not_a_flip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_harness(monkeypatch)
    monkeypatch.setitem(fakes.EFFECTS, ("s1", "b"), -400000.0)
    plan = make_plan()
    executor = GardenExecutor(FakeBackend(plan), plan, b"d")
    await executor.setup()
    baseline = await executor.run_universe(plan.default_choices(), "baseline")
    broken = await executor.run_universe({"s1": "b"}, "single")
    assert broken.status == "failed" and broken.result is None
    assert broken.error is not None and broken.error.startswith("implausible estimate")
    assert broken.flipped is None
    garden = fakes.Garden()
    garden.add(baseline)
    garden.baseline_id = baseline.id
    garden.add(broken)
    report = build_report(plan, garden, None)
    assert report.n_failed == 1 and report.failed[0].startswith("implausible estimate")
    assert report.n_flipped == 0 and robustness(garden) == 1.0
