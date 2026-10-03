from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def dry_run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["make", "-n", *args], cwd=ROOT, capture_output=True, text=True)


def test_scripted_benchmark_target_runs_the_two_scripted_datasets() -> None:
    done = dry_run("bench-blade-scripted", "BLADE_DIR=/blade")
    assert done.returncode == 0
    assert "bench blade --llm scripted --datasets hurricane,teachingratings" in done.stdout
    assert "--blade-dir /blade" in done.stdout


def test_live_benchmark_target_smokes_first_and_caps_spend() -> None:
    done = dry_run("bench-blade-live", "BLADE_DIR=/blade")
    lines = done.stdout.splitlines()
    smoke = next(i for i, line in enumerate(lines) if "live_smoke.py" in line)
    bench = next(i for i, line in enumerate(lines) if "bench blade --llm nebius" in line)
    assert smoke < bench
    assert "--max-usd 2.0" in lines[bench] or "--max-usd 2.0" in lines[bench + 1]
    assert "--datasets all" in done.stdout


def test_benchmark_targets_need_a_blade_clone() -> None:
    done = dry_run("bench-blade-scripted")
    assert done.returncode != 0 and "BLADE_DIR" in done.stderr


def test_hurricane_recordings_are_wired_without_touching_the_five_case_live_target() -> None:
    live = dry_run("record-live-hurricanes").stdout
    assert "record-demo --case hurricanes --llm nebius" in live
    assert "live_smoke.py" in live
    scripted = dry_run("record-demos").stdout
    assert "record-demo --case hurricanes --llm scripted" in scripted
    assert "hurricanes" not in dry_run("record-live").stdout
