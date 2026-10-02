from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from borges import cli
from tests.live_cases import LIVE_FLIP_UNIVERSE, make_cases_dir

runner = CliRunner()


@pytest.fixture
def live_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cases = make_cases_dir(tmp_path, scripted=False)
    monkeypatch.setenv("BORGES_CASES_DIR", str(cases))
    monkeypatch.setenv("BORGES_HOME", str(tmp_path / "home"))
    return cases


def test_reproduce_source_live_matches_the_live_flip(live_cases: Path) -> None:
    result = runner.invoke(
        cli.app,
        [
            "reproduce",
            "--case",
            "checkout_ab",
            "--universe",
            LIVE_FLIP_UNIVERSE,
            "--source",
            "live",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "MATCH" in result.output


def test_reproduce_default_source_is_scripted(live_cases: Path) -> None:
    result = runner.invoke(
        cli.app, ["reproduce", "--case", "checkout_ab", "--universe", LIVE_FLIP_UNIVERSE]
    )
    assert result.exit_code == 1
    assert "no committed scripted recording" in result.output


def test_reproduce_rejects_an_unknown_source(live_cases: Path) -> None:
    result = runner.invoke(
        cli.app,
        ["reproduce", "--case", "checkout_ab", "--universe", "u_x", "--source", "bogus"],
    )
    assert result.exit_code != 0
