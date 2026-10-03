from __future__ import annotations

from pathlib import Path

import pytest

from borges.cli_runtime import copy_recording
from borges.config import Settings


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=tmp_path / "cases",
    )


def make_run(settings: Settings, files: tuple[str, ...]) -> None:
    run = settings.borges_runs_dir / "r_1"
    run.mkdir(parents=True)
    for name in ("events.jsonl", *files):
        (run / name).write_text(f"{name}\n")


def test_live_recording_carries_spans_and_audit(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    make_run(settings, ("spans.jsonl", "audit.jsonl"))
    target = copy_recording(settings, "r_1", "demo", "nebius")
    assert target.parent.name == "recorded-live"
    assert (target.parent / "spans.jsonl").read_text() == "spans.jsonl\n"
    assert (target.parent / "audit.jsonl").read_text() == "audit.jsonl\n"


def test_stale_trace_files_are_removed_when_the_new_run_has_none(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    make_run(settings, ("spans.jsonl",))
    target = copy_recording(settings, "r_1", "demo", "nebius")
    (settings.borges_runs_dir / "r_1" / "spans.jsonl").unlink()
    copy_recording(settings, "r_1", "demo", "nebius")
    assert not (target.parent / "spans.jsonl").exists()


def test_missing_event_log_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        copy_recording(settings_for(tmp_path), "nope", "demo")
