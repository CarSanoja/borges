from __future__ import annotations

from borges.config import Settings
from borges.runtime.admission import make_admit
from borges.runtime.queue import JobQueue
from tests.runtime.conftest import new_job


def _job(db, clock, run_id: str, **overrides):
    queue = JobQueue(db, clock)
    queue.submit(new_job(run_id, **overrides))
    return queue.get(run_id)


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_total_active_cap(db, clock) -> None:
    admit = make_admit(_settings(borges_max_active_runs=2))
    candidate = _job(db, clock, "c")
    busy = [_job(db, clock, "a", owner_key="x"), _job(db, clock, "b", owner_key="y")]
    assert admit(candidate, busy[:1]) is True
    assert admit(candidate, busy) is False


def test_live_cap_only_counts_live_jobs(db, clock) -> None:
    admit = make_admit(_settings(borges_max_active_runs=5, borges_max_live_runs=1))
    live_running = [_job(db, clock, "a", live=True, owner_key="x")]
    assert admit(_job(db, clock, "scripted", owner_key="s"), live_running) is True
    assert admit(_job(db, clock, "live", live=True, owner_key="l"), live_running) is False


def test_anonymous_owner_has_one_active_run(db, clock) -> None:
    admit = make_admit(_settings(borges_max_active_runs=5, borges_anon_active_runs=1))
    running = [_job(db, clock, "a", owner_key="anon|1")]
    assert admit(_job(db, clock, "b", owner_key="anon|1"), running) is False
    assert admit(_job(db, clock, "c", owner_key="anon|2"), running) is True


def test_named_principals_get_a_larger_share(db, clock) -> None:
    admit = make_admit(_settings(borges_max_active_runs=10, borges_anon_active_runs=1))
    running = [_job(db, clock, f"r{i}", owner_key="caller://ci", anonymous=False) for i in range(3)]
    candidate = _job(db, clock, "next", owner_key="caller://ci", anonymous=False)
    assert admit(candidate, running) is True
    running.append(_job(db, clock, "r4", owner_key="caller://ci", anonymous=False))
    assert admit(candidate, running) is False
