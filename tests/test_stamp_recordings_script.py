from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stamp_recordings.py"


def load():
    spec = importlib.util.spec_from_file_location("stamp_recordings", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make(tmp_path: Path, with_meta: bool) -> tuple[Path, Path]:
    cases = tmp_path / "cases"
    runs = tmp_path / "runs"
    live = cases / "demo" / "recorded-live"
    live.mkdir(parents=True)
    (cases / "demo" / "case.json").write_text("{}")
    (live / "events.jsonl").write_text(json.dumps({"run_id": "r_9", "type": "run.started"}) + "\n")
    if with_meta:
        (runs / "r_9").mkdir(parents=True)
        meta = {"created_at": 1790892566.0, "llm": "nebius", "backend": "local", "cost_usd": 1.5}
        (runs / "r_9" / "meta.json").write_text(json.dumps(meta))
    return cases, runs


def test_stamps_from_meta_with_per_case_commit(tmp_path: Path) -> None:
    cases, runs = make(tmp_path, True)
    code = load().main(
        [
            "--cases-dir",
            str(cases),
            "--runs-dir",
            str(runs),
            "--commit",
            "aaa",
            "--commit",
            "demo=bbb",
        ]
    )
    stamp = json.loads((cases / "demo" / "recorded-live" / "recording.json").read_text())
    assert code == 0
    assert stamp["commit"] == "bbb" and stamp["run_id"] == "r_9" and stamp["backend"] == "local"
    assert stamp["cost_usd"] == 1.5 and stamp["registry_sha"] is None


def test_missing_meta_leaves_nulls_and_no_commit_is_null(tmp_path: Path) -> None:
    cases, runs = make(tmp_path, False)
    load().main(["--cases-dir", str(cases), "--runs-dir", str(runs)])
    stamp = json.loads((cases / "demo" / "recorded-live" / "recording.json").read_text())
    assert stamp["commit"] is None and stamp["recorded_at"] is None and stamp["llm"] is None
    assert stamp["run_id"] == "r_9" and stamp["case_id"] == "demo"
