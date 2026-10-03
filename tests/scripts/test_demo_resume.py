from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_the_makefile_has_a_demo_resume_target_that_runs_the_script() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "demo-resume:" in makefile and "scripts/demo_resume.py" in makefile
    assert "demo-resume" in makefile.split(".PHONY:")[1].splitlines()[0]


@pytest.mark.timeout(600)
def test_a_killed_worker_resumes_to_the_same_flip(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "demo_resume.py")],
        capture_output=True,
        text=True,
        timeout=580,
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "worker killed (SIGKILL)" in result.stdout
    assert "SAME FLIP after the kill and resume" in result.stdout
    assert "resumed=1" in result.stdout or "resumed=2" in result.stdout
