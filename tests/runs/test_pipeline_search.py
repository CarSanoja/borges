from __future__ import annotations

from pathlib import Path

import pytest

from borges.runs.models import RunRequest
from tests.runs.engine_fakes import install
from tests.runs.engine_scenario import Scenario
from tests.runs.fakes import make_rig


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> Scenario:
    value = Scenario()
    install(monkeypatch, value)
    return value


async def test_report_carries_the_search_summary_when_singles_flip(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    search = snapshot.report.search
    assert search is not None
    assert search.levels_explored == 1
    assert search.max_combinations_per_level == 10
    assert search.universe_budget > search.universes_used > 0
    assert search.universes_used <= len(snapshot.garden.universes)
    assert search.budget_exhausted is False


async def test_search_summary_counts_combination_levels(tmp_path: Path, scenario: Scenario) -> None:
    scenario.effects = {("s1", "b"): -0.6, ("s2", "y"): -0.6}
    scenario.combination_choices = [{"s1": "b", "s2": "y"}]
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    search = snapshot.report.search
    assert search is not None and search.levels_explored == 2
    assert search.budget_exhausted is False


async def test_budget_exhausted_is_reported(tmp_path: Path, scenario: Scenario) -> None:
    scenario.effects = {}
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo", max_universes=2))
    search = snapshot.report.search
    assert search is not None
    assert search.budget_exhausted is True
    assert search.universe_budget == 2 and search.universes_used == 2


async def test_finished_search_without_a_flip_is_not_budget_exhausted(
    tmp_path: Path, scenario: Scenario
) -> None:
    scenario.effects = {}
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    search = snapshot.report.search
    assert search is not None and search.budget_exhausted is False


async def test_coding_summary_and_smoke_events_reach_the_run(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    coding = snapshot.report.coding
    assert coding is not None and coding.options > 0
    assert coding.smoke_tested == coding.options
    smoke = [e.data for e in rig.store.events("r_test") if e.type == "option.smoke"]
    assert len(smoke) == coding.options
    assert {d["status"] for d in smoke} == {"passed"}
