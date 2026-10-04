from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from borges.config import Settings
from borges.identity.anon_live_quota import DAY_S, DB_NAME, HOUR_S, AnonLiveQuota


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


def make(tmp_path: Path, clock: Clock, **fields) -> AnonLiveQuota:
    settings = Settings(_env_file=None, borges_home=tmp_path, **fields)
    return AnonLiveQuota(settings, clock)


def use(quota: AnonLiveQuota, ip: str) -> None:
    quota.check(ip)
    quota.record(ip)


def test_the_third_live_run_from_one_client_in_a_day_is_refused(tmp_path: Path) -> None:
    clock = Clock()
    quota = make(tmp_path, clock)
    use(quota, "1.2.3.4")
    clock.now += 10
    use(quota, "1.2.3.4")
    with pytest.raises(HTTPException) as refused:
        quota.check("1.2.3.4")
    assert refused.value.status_code == 429
    assert "2 live runs per client per 24 hours" in refused.value.detail
    assert "resets at" in refused.value.detail
    assert int(refused.value.headers["Retry-After"]) == int(DAY_S - 10) + 1


def test_other_clients_are_not_affected(tmp_path: Path) -> None:
    quota = make(tmp_path, Clock())
    use(quota, "1.2.3.4")
    use(quota, "1.2.3.4")
    quota.check("5.6.7.8")


def test_the_window_slides_after_a_day(tmp_path: Path) -> None:
    clock = Clock()
    quota = make(tmp_path, clock)
    use(quota, "1.2.3.4")
    use(quota, "1.2.3.4")
    clock.now += DAY_S + 1
    quota.check("1.2.3.4")
    assert quota.view("1.2.3.4").remaining == 2


def test_the_global_hourly_cap_applies_across_clients(tmp_path: Path) -> None:
    clock = Clock()
    quota = make(tmp_path, clock, borges_anon_live_global_per_hour=3)
    for index in range(3):
        use(quota, f"10.0.0.{index}")
    with pytest.raises(HTTPException) as refused:
        quota.check("10.0.0.9")
    assert "per hour on this server" in refused.value.detail
    clock.now += HOUR_S + 1
    quota.check("10.0.0.9")


def test_zero_disables_anonymous_live_runs(tmp_path: Path) -> None:
    quota = make(tmp_path, Clock(), borges_anon_live_per_client_per_day=0)
    with pytest.raises(HTTPException):
        quota.check("1.2.3.4")


def test_the_store_is_durable_and_never_holds_the_raw_address(tmp_path: Path) -> None:
    clock = Clock()
    use(make(tmp_path, clock), "203.0.113.77")
    reopened = make(tmp_path, clock)
    assert reopened.view("203.0.113.77").remaining == 1
    rows = (
        sqlite3.connect(tmp_path / DB_NAME).execute("SELECT ip_hash, ts FROM anon_live").fetchall()
    )
    assert len(rows) == 1 and "203.0.113.77" not in rows[0][0] and len(rows[0][0]) == 32
    raw = b"".join(p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    assert b"203.0.113.77" not in raw


def test_the_hash_is_salted(tmp_path: Path) -> None:
    clock = Clock()
    first = make(tmp_path / "a", clock, borges_ip_hash_salt="one")
    second = make(tmp_path / "b", clock, borges_ip_hash_salt="two")
    assert first.client_hash("1.2.3.4") != second.client_hash("1.2.3.4")
    auto = make(tmp_path / "c", clock)
    assert auto.client_hash("1.2.3.4") == make(tmp_path / "c", clock).client_hash("1.2.3.4")


def test_the_view_states_cost_and_remaining(tmp_path: Path) -> None:
    quota = make(tmp_path, Clock(), borges_run_cap_usd=0.5)
    use(quota, "1.2.3.4")
    view = quota.view("1.2.3.4").as_dict()
    assert view["remaining"] == 1 and view["est_cost_per_run_usd"] == 0.5
    assert view["resets_at"] is not None and view["global_remaining"] == 5
