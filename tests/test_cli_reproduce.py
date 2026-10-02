from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from borges import cli
from borges.config import REPO_ROOT

runner = CliRunner()


def _flip_id(case_id: str) -> str:
    path = REPO_ROOT / "cases" / case_id / "recorded" / "events.jsonl"
    for raw in path.read_text().splitlines():
        event = json.loads(raw)
        if event["type"] == "flip.verified":
            return event["data"]["flip"]["universe_id"]
    raise AssertionError("recording has no verified flip")


FLIP = {"checkout_ab": _flip_id("checkout_ab"), "red_cards": _flip_id("red_cards")}


@pytest.fixture
def cases_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "cases"
    shutil.copytree(
        REPO_ROOT / "cases" / "checkout_ab",
        target / "checkout_ab",
        ignore=shutil.ignore_patterns("fixtures", "__pycache__", "*.py"),
    )
    monkeypatch.setenv("BORGES_CASES_DIR", str(target))
    monkeypatch.setenv("BORGES_HOME", str(tmp_path / "home"))
    return target


def test_reproduce_the_checkout_flip_matches_the_recording(cases_copy: Path) -> None:
    result = runner.invoke(
        cli.app, ["reproduce", "--case", "checkout_ab", "--universe", FLIP["checkout_ab"]]
    )
    assert result.exit_code == 0, result.output
    assert "MATCH" in result.output
    assert "reproduced" in result.output
    assert "estimate" in result.output


def _tamper(cases: Path) -> None:
    path = cases / "checkout_ab" / "recorded" / "events.jsonl"
    lines = []
    for raw in path.read_text().splitlines():
        event = json.loads(raw)
        universe = event["data"].get("universe")
        if event["type"] == "universe.finished" and universe["id"] == FLIP["checkout_ab"]:
            universe["result"]["estimate"] += 0.25
        lines.append(json.dumps(event))
    path.write_text("\n".join(lines) + "\n")


def test_reproduce_exits_non_zero_when_the_recording_disagrees(cases_copy: Path) -> None:
    _tamper(cases_copy)
    result = runner.invoke(
        cli.app, ["reproduce", "--case", "checkout_ab", "--universe", FLIP["checkout_ab"]]
    )
    assert result.exit_code == 1
    assert "MISMATCH" in result.output
    assert "estimate" in result.output


def test_reproduce_rejects_an_unknown_universe_and_case(cases_copy: Path) -> None:
    bad_universe = runner.invoke(
        cli.app, ["reproduce", "--case", "checkout_ab", "--universe", "u_nope"]
    )
    bad_case = runner.invoke(cli.app, ["reproduce", "--case", "nope", "--universe", "u_nope"])
    assert bad_universe.exit_code == 1
    assert "unknown universe" in bad_universe.output
    assert bad_case.exit_code == 1
