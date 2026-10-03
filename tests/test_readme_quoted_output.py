from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from borges.config import REPO_ROOT

README = REPO_ROOT / "README.md"
TAIL_LINES = 2


def readme_lines() -> set[str]:
    lines = README.read_text(encoding="utf-8").splitlines()
    return {line.removeprefix(">").strip() for line in lines}


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
        assert line.strip() in quoted, f"README does not quote the real output line: {line!r}"


def test_readme_names_the_same_first_commands_the_test_runs() -> None:
    text = README.read_text(encoding="utf-8")
    assert "uv run borges run --case marp_norms --llm scripted" in text
    reproduce = "uv run borges reproduce --case checkout_ab --source live"
    assert f"{reproduce} --universe u_3a4a8a35a5" in text


def test_readme_makes_no_unprompted_discovery_claim() -> None:
    text = README.read_text(encoding="utf-8").lower()
    assert "found the planted" not in text
    assert "on its own" not in text
