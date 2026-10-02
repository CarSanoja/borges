from __future__ import annotations

import pytest
from typer.testing import CliRunner

from borges.cli import app
from borges.config import Settings
from borges.identity.keystore import open_keystore
from borges.runs.store import RunStore
from borges.runtime.db import open_runtime_db
from borges.runtime.dead_letter import DeadLetters
from borges.runtime.jobs import DEAD, QUEUED
from borges.runtime.queue import JobQueue
from borges.runtime.schedules import ScheduleStore
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path
from tests.runtime.conftest import allow_all, new_job

runner = CliRunner()


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("BORGES_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BORGES_RUNS_DIR", str(tmp_path / "runs"))
    return Settings(
        _env_file=None, borges_home=tmp_path / "home", borges_runs_dir=tmp_path / "runs"
    )


def bury(home: Settings, run_id: str = "r_dead") -> None:
    db = open_runtime_db(home)
    queue = JobQueue(db)
    queue.submit(new_job(run_id))
    queue.claim("w", 30, allow_all)
    DeadLetters(db).bury(run_id, "w", "Nebius 503", {"key": "universe:u_1"})
    store = RunStore(home.borges_runs_dir)
    store.create(run_id, {"status": "failed"})


def test_dead_letter_listing(home: Settings) -> None:
    empty = runner.invoke(app, ["runs", "dead-letter"])
    assert empty.exit_code == 0 and "empty" in empty.output
    bury(home)
    listed = runner.invoke(app, ["runs", "dead-letter"])
    assert "r_dead\t1 attempts\tNebius 503" in listed.output


def test_retry_requeues_the_run_and_audits_it(home: Settings) -> None:
    bury(home)
    result = runner.invoke(app, ["runs", "retry", "r_dead"])
    assert result.exit_code == 0, result.output
    assert "requeued r_dead" in result.output
    assert JobQueue(open_runtime_db(home)).get("r_dead").state == QUEUED
    assert RunStore(home.borges_runs_dir).meta("r_dead")["status"] == "queued"
    kinds = [r.kind for r in read_records(global_audit_path(home))]
    assert "runtime.run.requeue" in kinds
    assert runner.invoke(app, ["runs", "dead-letter"]).output.startswith("the dead-letter")


def test_retry_of_a_run_that_is_not_dead_fails(home: Settings) -> None:
    result = runner.invoke(app, ["runs", "retry", "r_unknown"])
    assert result.exit_code == 2 and "not a dead-lettered" in result.output
    queue = JobQueue(open_runtime_db(home))
    queue.submit(new_job("r_fine"))
    assert runner.invoke(app, ["runs", "retry", "r_fine"]).exit_code == 2
    assert DEAD == "dead"


def test_work_returns_when_the_queue_is_empty(home: Settings) -> None:
    result = runner.invoke(app, ["runs", "work", "--wait", "5"])
    assert result.exit_code == 0 and "0 run(s) still active" in result.output


def test_schedule_add_list_and_remove(home: Settings) -> None:
    added = runner.invoke(app, ["schedule", "add", "--case", "checkout_ab", "--every", "24h"])
    assert added.exit_code == 0, added.output
    schedule_id = added.output.split("\t")[0]
    assert schedule_id.startswith("sch_") and "every 24h" in added.output
    [stored] = ScheduleStore(open_runtime_db(home)).entries()
    assert stored.principal == "operator" and stored.every_s == 86400.0
    listed = runner.invoke(app, ["schedule", "list"])
    assert f"{schedule_id}\tcheckout_ab\tevery 86400s" in listed.output
    kinds = [r.kind for r in read_records(global_audit_path(home))]
    assert "runtime.schedule.added" in kinds
    removed = runner.invoke(app, ["schedule", "remove", schedule_id])
    assert (
        removed.exit_code == 0
        and runner.invoke(app, ["schedule", "list"]).output == "no schedules\n"
    )
    assert runner.invoke(app, ["schedule", "remove", schedule_id]).exit_code == 2


@pytest.mark.parametrize(
    "args",
    [
        ["--every", "soon"],
        ["--every", "10s"],
        ["--every", "1h", "--llm", "local"],
    ],
)
def test_schedule_add_rejects_bad_input(home: Settings, args: list[str]) -> None:
    result = runner.invoke(app, ["schedule", "add", "--case", "checkout_ab", *args])
    assert result.exit_code == 2
    assert ScheduleStore(open_runtime_db(home)).entries() == []


def test_schedule_runs_as_the_key_principal_and_refuses_a_bad_key(home: Settings) -> None:
    _, token = open_keystore(home).create("nightly", "runs:create:scripted", None)
    ok = runner.invoke(
        app, ["schedule", "add", "--case", "checkout_ab", "--every", "1h", "--key", token]
    )
    assert ok.exit_code == 0, ok.output
    [stored] = ScheduleStore(open_runtime_db(home)).entries()
    assert stored.principal == "caller://nightly"
    bad = runner.invoke(
        app, ["schedule", "add", "--case", "checkout_ab", "--every", "1h", "--key", "bk_nope"]
    )
    assert bad.exit_code == 2 and "rejected" in bad.output
    assert len(ScheduleStore(open_runtime_db(home)).entries()) == 1
