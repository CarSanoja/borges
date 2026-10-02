from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from borges import cli
from borges.config import Settings
from borges.runs.store import RunStore
from borges.telemetry.audit_log import AuditLog
from borges.telemetry.run_telemetry import global_audit_path, run_audit_path

runner = CliRunner()


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    value = Settings(
        _env_file=None, borges_home=tmp_path / "home", borges_runs_dir=tmp_path / "runs"
    )
    monkeypatch.setattr("borges.cli_audit.get_settings", lambda: value)
    RunStore(value.borges_runs_dir).create("r1", {})
    for path in (run_audit_path(value, "r1"), global_audit_path(value)):
        log = AuditLog(path)
        for index in range(3):
            log.append("model.call", data={"i": index})
    return value


def test_verify_run_and_global_ok(settings: Settings) -> None:
    for target in ("r1", "global"):
        result = runner.invoke(cli.app, ["audit", "verify", target])
        assert result.exit_code == 0, result.output
        assert result.output.startswith("OK 3 records")


def test_verify_reports_the_first_broken_link(settings: Settings) -> None:
    path = run_audit_path(settings, "r1")
    lines = path.read_text().splitlines()
    record = json.loads(lines[1])
    record["data"]["i"] = 99
    lines[1] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n")
    result = runner.invoke(cli.app, ["audit", "verify", "r1"])
    assert result.exit_code == 1
    assert "BROKEN at seq 2" in result.output and "1 records verified" in result.output


def test_unknown_run_and_missing_log(settings: Settings) -> None:
    assert runner.invoke(cli.app, ["audit", "verify", "nope"]).exit_code == 2
    RunStore(settings.borges_runs_dir).create("r2", {})
    result = runner.invoke(cli.app, ["audit", "verify", "r2"])
    assert result.exit_code == 2 and "no audit log" in result.output
