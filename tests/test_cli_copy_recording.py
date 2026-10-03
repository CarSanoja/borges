from __future__ import annotations

import json
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


def write_meta(settings: Settings, **extra: object) -> None:
    meta = {
        "run_id": "r_1",
        "case_id": "demo",
        "created_at": 1790892566.0,
        "llm": "nebius",
        "backend": "local",
        "cost_usd": 0.5,
        "n_universes": 6,
        "verdict": "A",
        "flipped_verdict": "B",
        "agents": {"registry_sha": "abc"},
        **extra,
    }
    (settings.borges_runs_dir / "r_1" / "meta.json").write_text(json.dumps(meta))


def test_copy_writes_recording_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BORGES_COMMIT", "deadbee")
    settings = settings_for(tmp_path)
    make_run(settings, ())
    write_meta(settings)
    target = copy_recording(settings, "r_1", "demo", "nebius")
    stamp = json.loads((target.parent / "recording.json").read_text())
    assert stamp["commit"] == "deadbee"
    assert stamp["registry_sha"] == "abc"
    assert stamp["recorded_at"].startswith("2026-")
    assert stamp["backend"] == "local"
    assert stamp["n_universes"] == 6
    assert stamp["flipped_verdict"] == "B"
    assert stamp["dirty"] in (True, False, None)


def test_copy_without_meta_or_git_still_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("BORGES_COMMIT", raising=False)
    monkeypatch.setattr("borges.cases.recording_stamp.REPO_ROOT", tmp_path / "missing")
    settings = settings_for(tmp_path)
    make_run(settings, ())
    target = copy_recording(settings, "r_1", "demo", "nebius")
    stamp = json.loads((target.parent / "recording.json").read_text())
    assert stamp["commit"] is None
    assert stamp["dirty"] is None
    assert stamp["recorded_at"] is None
    assert stamp["run_id"] == "r_1"
