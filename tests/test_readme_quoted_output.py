from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from borges.config import REPO_ROOT

README = REPO_ROOT / "README.md"
CHECKPOINTS = re.compile(r"checkpoints: \d+")
CHECKOUT_LIVE = REPO_ROOT / "cases" / "checkout_ab" / "recorded-live" / "events.jsonl"
TAIL_LINES = 2


def recorded_flip_universe() -> str:
    events = [json.loads(line) for line in CHECKOUT_LIVE.read_text(encoding="utf-8").splitlines()]
    report = [e for e in events if e["type"] == "report.ready"][-1]["data"]["report"]
    return report["minimal_flip"]["universe_id"]


def _unscheduled(line: str) -> str:
    """The checkpoint count follows the order the universes ran in, which the scheduler and the
    prefix cache set: the same replay wrote 171 on the Mac and 163 on Linux (9 October)."""
    return CHECKPOINTS.sub("checkpoints: N", line.strip())


def readme_lines() -> set[str]:
    lines = README.read_text(encoding="utf-8").splitlines()
    return {_unscheduled(line.removeprefix(">")) for line in lines}


@pytest.mark.timeout(600)
def test_first_command_tail_in_the_readme_is_the_real_output(tmp_path: Path) -> None:
    env = {**os.environ, "BORGES_RUNS_DIR": str(tmp_path / "runs")}
    env["BORGES_HOME"] = str(tmp_path / "home")
    code = "from borges.cli import app; app()"
    command = [sys.executable, "-c", code, "run", "--case", "marp_norms", "--llm", "scripted"]
    result = subprocess.run(
        command, env=env, capture_output=True, text=True, cwd=REPO_ROOT, timeout=900
    )
    assert result.returncode == 0, result.stderr
    tail = [line for line in result.stdout.splitlines() if line.strip()][-TAIL_LINES:]
    quoted = readme_lines()
    for line in tail:
        assert _unscheduled(line) in quoted, f"README does not quote the real output line: {line!r}"


def test_the_live_replay_tail_in_the_readme_is_the_real_output(tmp_path: Path) -> None:
    env = {**os.environ, "BORGES_HOME": str(tmp_path / "home")}
    code = "from borges.cli import app; app()"
    command = [sys.executable, "-c", code, "replay", "--case", "checkout_ab"]
    result = subprocess.run(
        command, env=env, capture_output=True, text=True, cwd=REPO_ROOT, timeout=120
    )
    assert result.returncode == 0, result.stderr
    tail = [line for line in result.stdout.splitlines() if line.strip()][-TAIL_LINES:]
    quoted = readme_lines()
    for line in tail:
        assert _unscheduled(line) in quoted, f"README does not quote the real output line: {line!r}"


def test_readme_names_the_same_first_commands_the_test_runs() -> None:
    text = README.read_text(encoding="utf-8")
    assert "uv run borges run --case marp_norms --llm scripted" in text
    assert "uv run borges replay --case checkout_ab" in text
    reproduce = "uv run borges reproduce --case checkout_ab --source live"
    assert f"{reproduce} --universe {recorded_flip_universe()}" in text


def test_readme_makes_no_unprompted_discovery_claim() -> None:
    text = README.read_text(encoding="utf-8").lower()
    assert "found the planted" not in text
    assert "on its own" not in text
