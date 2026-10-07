from __future__ import annotations

import pytest

from borges.garden.influence import build_report, decision_influence, robustness
from borges.garden.models import Garden
from borges.garden.search import minimal_flip
from tests.garden.fakes import FakeBackend, build_garden, install_fake_harness, make_plan


@pytest.fixture(autouse=True)
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_harness(monkeypatch)


async def test_decision_influence_sorted_by_max_delta() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan), with_pairs=True)
    rows = decision_influence(plan, garden)
    assert [r.step_id for r in rows] == ["s3", "s2", "s1"]
    s3 = rows[0]
    assert s3.max_abs_delta == pytest.approx(2.1)
    assert s3.mean_abs_delta == pytest.approx(1.2)
    assert s3.flips == 1 and s3.n_alternatives == 2
    assert rows[1].flips == 1 and rows[1].n_alternatives == 1
    assert rows[2].flips == 0 and rows[2].title == "Filter"


async def test_decision_influence_empty_without_baseline() -> None:
    assert decision_influence(make_plan(), Garden()) == []


async def test_robustness_is_share_matching_baseline() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan))
    assert robustness(garden) == pytest.approx(3 / 5)


async def test_robustness_excludes_verification_and_failures() -> None:
    plan = make_plan()
    executor, garden = await build_garden(plan, FakeBackend(plan))
    verification = await executor.run_universe(
        {**plan.default_choices(), "s3": "o", "s1": "b"}, "verification"
    )
    garden.add(verification)
    assert robustness(garden) == pytest.approx(3 / 5)
    assert robustness(Garden()) == 1.0


async def test_build_report_assembles_counts() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan))
    flip = minimal_flip(plan, garden)
    report = build_report(plan, garden, flip)
    assert report.question == plan.question
    assert report.original_verdict == "SHIP"
    assert report.minimal_flip == flip
    assert report.n_universes == 5 and report.n_flipped == 2
    assert report.robustness_beam == pytest.approx(3 / 5)
    assert report.robustness_design == pytest.approx((1.0 + 0.5 + 2 / 3) / 3)
    assert report.robustness == report.robustness_design
    assert report.robustness_basis == "design_weighted"
    assert report.n_distinct_results == 5
    assert report.robustness_rating is None
    assert report.robustness_rating_reason == "n=5, too few to rate"
    assert report.narrative == ""
    assert [i.step_id for i in report.influences] == ["s3", "s2", "s1"]


def test_build_report_requires_baseline() -> None:
    with pytest.raises(ValueError):
        build_report(make_plan(), Garden(), None)


async def test_build_report_lists_failed_universes_and_excludes_them_from_robustness() -> None:
    plan = make_plan()
    backend = FakeBackend(plan, fail={("s2", "y")})
    _, garden = await build_garden(plan, backend)
    report = build_report(plan, garden, minimal_flip(plan, garden))
    assert report.n_failed == 1
    assert len(report.failed) == 1
    assert report.failed[0].startswith("s2/y: ")
    assert "\n" not in report.failed[0]
    assert report.n_universes == len(garden.finished())
    assert report.robustness_beam == pytest.approx(
        sum(1 for u in garden.finished() if u.verdict == garden.baseline.verdict)
        / len(garden.finished())
    )


async def test_build_report_without_failures_has_empty_failed() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan))
    report = build_report(plan, garden, None)
    assert report.n_failed == 0 and report.failed == []
