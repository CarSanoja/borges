from __future__ import annotations

import pytest

from borges.bench.blade_matcher import MatchPair
from borges.bench.blade_metrics import evaluate, harmonic, kind_metrics, mean_f1
from tests.bench.support import FakeMatcher


def test_harmonic_mean_handles_zero() -> None:
    assert harmonic(0, 0) == 0.0
    assert harmonic(1.0, 0.5) == pytest.approx(2 / 3)


def test_coverage_and_hit_rate_follow_blade_definitions() -> None:
    expert = ["IV: a", "DV: b", "Control: c", "Control: d"]
    runs = [["IV: x", "DV: y"], ["IV: x", "Control: z", "Control: w"]]
    unique = ["IV: x", "DV: y", "Control: z", "Control: w"]
    pairs = {"cvar": [MatchPair(0, 0, 9), MatchPair(1, 1, 8), MatchPair(2, 2, 7)]}
    metrics = kind_metrics("cvar", expert, runs, pairs, unique)
    assert metrics.matched_expert == 2
    assert metrics.coverage == pytest.approx(0.5)
    assert metrics.hit_rate == pytest.approx((1.0 + 1 / 3) / 2)
    assert metrics.f1 == pytest.approx(harmonic(0.5, (1.0 + 1 / 3) / 2))


def test_model_coverage_is_capped_by_the_number_of_runs() -> None:
    expert = ["m1", "m2", "m3", "m4"]
    runs = [["a"], ["b"]]
    pairs = {"model": [MatchPair(0, 0, 10), MatchPair(1, 1, 10)]}
    metrics = kind_metrics("model", expert, runs, pairs, ["a", "b"])
    assert metrics.coverage == 1.0


def test_empty_runs_score_zero() -> None:
    metrics = kind_metrics("transform", ["t"], [[]], {}, [])
    assert (metrics.coverage, metrics.hit_rate, metrics.f1) == (0.0, 0.0, 0.0)


async def test_evaluate_calls_the_matcher_once_per_kind_on_unique_items() -> None:
    matcher = FakeMatcher()
    expert = {
        "cvar": ["IV: feminity metric of hurricane name", "Control: year of hurricane."],
        "model": ["negative binomial regression"],
        "transform": ["Remove hurricane Katrina from the dataset."],
    }
    runs = [
        {
            "cvar": ["IV: femininity rating", "Control: year"],
            "model": ["negative binomial"],
            "transform": ["drop the deadliest storm"],
        },
        {
            "cvar": ["IV: femininity rating"],
            "model": ["negative binomial"],
            "transform": ["keep everything"],
        },
    ]
    metrics = await evaluate(matcher, "q", "schema", expert, runs)
    assert matcher.seen == ["cvar", "model", "transform"]
    assert metrics["cvar"]["coverage"] == 1.0
    assert metrics["cvar"]["n_agent_items"] == 2
    assert metrics["model"]["hit_rate"] == 1.0
    assert metrics["transform"]["coverage"] == 1.0
    assert metrics["transform"]["hit_rate"] == pytest.approx(0.5)
    assert 0 < mean_f1(metrics) <= 1
