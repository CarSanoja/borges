from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from borges import cli
from borges.config import Settings
from borges.fleet import locations

runner = CliRunner()


@pytest.fixture
def empty_home(settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setattr("borges.fleet.cli.get_settings", lambda: settings)
    monkeypatch.setattr(locations, "SEED_PATH", tmp_path / "empty_seed.jsonl")
    return settings


def test_publish_twice_second_is_a_no_op(empty_home: Settings) -> None:
    first = runner.invoke(cli.app, ["agents", "publish"])
    assert first.exit_code == 0 and first.output.count("published") == 12
    second = runner.invoke(cli.app, ["agents", "publish"])
    assert second.exit_code == 0 and "nothing to publish" in second.output


def test_approve_and_retire(empty_home: Settings) -> None:
    runner.invoke(cli.app, ["agents", "publish"])
    approved = runner.invoke(cli.app, ["agents", "approve", "judge", "1.0.0"])
    assert approved.exit_code == 0 and "approved" in approved.output
    listing = runner.invoke(cli.app, ["agents", "list"])
    assert "judge\tactive\t1.0.0 approved" in listing.output
    retired = runner.invoke(cli.app, ["agents", "retire", "judge", "1.0.0"])
    assert retired.exit_code == 0 and "retired" in retired.output
    again = runner.invoke(cli.app, ["agents", "approve", "judge", "1.0.0"])
    assert again.exit_code == 1


def test_unknown_version_exits_2(empty_home: Settings) -> None:
    result = runner.invoke(cli.app, ["agents", "approve", "judge", "7.0.0"])
    assert result.exit_code == 2


def test_publish_with_approve_flag(empty_home: Settings) -> None:
    result = runner.invoke(cli.app, ["agents", "publish", "--approve"])
    assert result.output.count("approved") == 12
