from __future__ import annotations

from pathlib import Path

import pytest

from borges.runtime.db import RuntimeDb
from borges.runtime.jobs import NewJob


class Clock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def db(tmp_path: Path) -> RuntimeDb:
    return RuntimeDb(tmp_path / "runtime" / "runtime.db")


def new_job(run_id: str = "r1", **overrides) -> NewJob:
    fields = {
        "run_id": run_id,
        "principal": "caller://anonymous",
        "owner_key": "caller://anonymous|1.2.3.4",
        "anonymous": True,
        "live": False,
        "request": '{"case_id": "demo"}',
        "max_attempts": 3,
    }
    return NewJob(**{**fields, **overrides})


def allow_all(job, running) -> bool:
    return True
