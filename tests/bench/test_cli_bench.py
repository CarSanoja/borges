from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from borges.cli import app
from tests.bench.support import MINI

runner = CliRunner()


def test_bench_blade_is_a_registered_command() -> None:
    result = runner.invoke(app, ["bench", "blade", "--help"])
    assert result.exit_code == 0
    for flag in ("--datasets", "--arms", "--llm", "--out", "--max-usd", "--repeats"):
        assert flag in result.output


def test_live_run_over_budget_is_refused_before_any_call(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "bench",
            "blade",
            "--datasets",
            "hurricane,teachingratings",
            "--llm",
            "nebius",
            "--matcher",
            "lexical",
            "--max-usd",
            "0.01",
            "--blade-dir",
            str(MINI),
            "--out",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code == 1
    assert "exceeds --max-usd" in result.output
    assert not (tmp_path / "out" / "runs").exists()


def test_missing_blade_directory_exits_cleanly(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BORGES_BLADE_DIR", raising=False)
    result = runner.invoke(app, ["bench", "blade", "--out", str(tmp_path / "out")])
    assert result.exit_code == 1
    assert "BLADE data not found" in result.output


def test_unknown_arm_is_rejected(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["bench", "blade", "--arms", "oracle", "--blade-dir", str(MINI), "--out", str(tmp_path)],
    )
    assert result.exit_code == 1 and "unknown arm" in result.output


@pytest.mark.timeout(600)
def test_scripted_command_runs_end_to_end_without_network(tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "bench",
            "blade",
            "--datasets",
            "teachingratings",
            "--arms",
            "planner",
            "--llm",
            "scripted",
            "--blade-dir",
            str(MINI),
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    summary = json.loads((out / "summary.json").read_text())
    assert summary["rows"][0]["dataset"] == "teachingratings"
    assert summary["total_cost_usd"] == 0
    assert "plumbing check" in summary["matcher"]
    assert "| teachingratings | planner |" in result.output
