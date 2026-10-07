from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from borges import cli

runner = CliRunner()


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BORGES_HOME", str(tmp_path / "home"))


def test_replay_prints_the_live_recording_the_web_app_plays() -> None:
    result = runner.invoke(cli.app, ["replay", "--case", "checkout_ab"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("Live recording of 2026-10-05T22:47:27Z")
    assert "no model is called" in result.output
    assert "Models: planner nvidia/nemotron-3-super-120b-a12b" in result.output
    assert "SHIP -> DON'T SHIP" in result.output
    assert "estimated cost: $0.0291" in result.output


def test_replay_of_the_scripted_recording_says_so() -> None:
    result = runner.invoke(cli.app, ["replay", "--case", "checkout_ab", "--source", "scripted"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("Scripted recording")
    assert "(scripted replay, no model called)" in result.output


def test_a_live_only_case_has_no_scripted_recording_to_replay() -> None:
    result = runner.invoke(
        cli.app, ["replay", "--case", "bank_marketing_calls", "--source", "scripted"]
    )
    assert result.exit_code == 1
    assert "has no committed scripted recording" in result.output


def test_an_unknown_source_is_refused() -> None:
    result = runner.invoke(cli.app, ["replay", "--case", "checkout_ab", "--source", "cache"])
    assert result.exit_code != 0
