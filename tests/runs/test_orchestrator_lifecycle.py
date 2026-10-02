from __future__ import annotations

import asyncio
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


async def test_active_and_live_counts_come_from_running_tasks(
    tmp_path: Path, scenario: Scenario
) -> None:
    rig = make_rig(tmp_path)
    scenario.hang = True
    assert (rig.orchestrator.active_count(), rig.orchestrator.live_count()) == (0, 0)
    await rig.orchestrator.start(RunRequest(case_id="demo", llm="scripted"))
    await rig.orchestrator.start(RunRequest(case_id="demo", llm="nebius"))
    assert (rig.orchestrator.active_count(), rig.orchestrator.live_count()) == (2, 1)
    await rig.orchestrator.shutdown()
    await asyncio.sleep(0)
    assert (rig.orchestrator.active_count(), rig.orchestrator.live_count()) == (0, 0)


async def test_failed_append_in_finish_still_drops_the_bus_channel(
    tmp_path: Path, scenario: Scenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = make_rig(tmp_path)
    real_append = rig.store.append

    def append(event) -> None:
        if event.type == "run.finished":
            raise OSError("no space left on device")
        real_append(event)

    monkeypatch.setattr(rig.store, "append", append)
    with pytest.raises(OSError):
        await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    assert not rig.bus.is_live("r_test")
    assert rig.store.meta("r_test")["status"] == "completed"
