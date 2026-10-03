from __future__ import annotations

import pytest

from borges.identity.principal import ANONYMOUS
from borges.runtime.jobs import RUNNING
from tests.runtime.fake_runtime import REQUEST, make_fake_runtime
from tests.runtime.rig import wait_for

pytestmark = pytest.mark.timeout(60)


def lapse(runtime, run_id: str) -> None:
    with runtime.db.transaction() as conn:
        conn.execute("UPDATE jobs SET lease_expires = 1 WHERE run_id = ?", (run_id,))


async def test_a_late_heartbeat_does_not_start_the_same_run_twice(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.scenario.hang = True
    result = await fake.runtime.submit(REQUEST, ANONYMOUS, "10.0.0.1")
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    lapse(fake.runtime, result.run_id)
    fake.runtime.maintain()
    await fake.runtime.dispatch()
    fake.runtime.maintain()
    await fake.runtime.dispatch()
    assert fake.scenario.calls.count("plan_analysis") == 1
    assert fake.runtime.queue.get(result.run_id).state == RUNNING
    assert fake.runtime.queue.get(result.run_id).attempts == 1
    await fake.runtime.stop()


async def test_a_cancelled_run_is_never_claimed_again(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.scenario.hang = True
    result = await fake.runtime.submit(REQUEST, ANONYMOUS, "10.0.0.1")
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    await fake.runtime.cancel(result.run_id)
    fake.rig.orchestrator.tasks[result.run_id].cancel()
    await wait_for(lambda: fake.runtime.queue.get(result.run_id).state != RUNNING)
    lapse(fake.runtime, result.run_id)
    fake.runtime.maintain()
    assert await fake.runtime.dispatch() == 0
    assert fake.scenario.calls.count("plan_analysis") == 1
    assert fake.runtime.queue.get(result.run_id).attempts == 1
    await fake.runtime.stop()
