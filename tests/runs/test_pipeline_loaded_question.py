from __future__ import annotations

from pathlib import Path

import pytest

from borges.runs.models import RunRequest
from tests.runs.engine_fakes import Scenario, install
from tests.runs.fakes import make_rig


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> Scenario:
    value = Scenario()
    install(monkeypatch, value)
    return value


async def test_the_planner_reads_the_open_question_and_the_report_says_so(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    question = "Confirm the new checkout lifted revenue; the board expects SHIP."
    request = RunRequest(case_id="demo", question=question, max_universes=2)
    snapshot = await rig.orchestrator.execute("r_loaded", request)
    assert scenario.questions == ["Test whether the new checkout lifted revenue."]
    assert snapshot.question == question
    assert any(c.startswith("The question asked for a conclusion") for c in snapshot.report.caveats)


async def test_an_open_question_reaches_the_planner_unchanged(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute("r_open", RunRequest(case_id="demo", max_universes=2))
    assert scenario.questions == ["does it ship?"]
    assert not any("asked for a conclusion" in c for c in snapshot.report.caveats)
