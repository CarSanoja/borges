from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "live_runs_table", ROOT / "scripts" / "live_runs_table.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def result(estimate: float) -> dict[str, Any]:
    return {
        "estimate": estimate,
        "ci_low": estimate - 1,
        "ci_high": estimate + 1,
        "p_value": 0.2,
        "n": 100,
    }


def universe(uid: str, estimate: float, changed: list[str], status: str = "done") -> dict:
    return {
        "type": "universe.finished",
        "data": {
            "universe": {
                "id": uid,
                "changed": changed,
                "status": status,
                "result": result(estimate),
            }
        },
    }


def write(folder: Path, flip: dict[str, Any] | None) -> Path:
    live = folder / "case_a" / "recorded-live"
    live.mkdir(parents=True)
    report = {
        "original_verdict": "SHIP",
        "original_result": result(0.5),
        "minimal_flip": flip,
        "n_universes": 3,
    }
    events = [
        universe("u_base", 0.5, []),
        universe("u_near", 0.6, ["s1"]),
        universe("u_far", -2.0, ["s2"]),
        universe("u_bad", 9.0, ["s3"], status="failed"),
        {
            "type": "usage",
            "data": {
                "llm_calls": 30,
                "cached_calls": 0,
                "tokens_in": 50000,
                "tokens_out": 4000,
                "cost_usd": 0.02,
            },
        },
        {"type": "report.ready", "data": {"report": report}},
    ]
    (live / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    recording = {"run_id": "r_1", "case_id": "case_a", "commit": "abc1234"}
    (live / "recording.json").write_text(json.dumps(recording))
    return live


def test_without_a_flip_the_farthest_finished_universe_is_listed(tmp_path: Path) -> None:
    module = load()
    row = module.load(write(tmp_path, None))
    assert row["ids"] == ["u_base", "u_far"] and row["failed"] == 1
    text = module.render([row])
    assert "| case_a | r_1 | `abc1234` | 30 (0) | 50,000 / 4,000 | $0.0200 | 3 (1) |" in text
    assert "| case_a | SHIP: 0.5 [-0.5, 1.5], p 0.2, n 100 | none | `u_base`, `u_far` |" in text


def test_a_flip_names_its_changes_and_its_universe(tmp_path: Path) -> None:
    module = load()
    flip = {
        "universe_id": "u_near",
        "flipped_verdict": "DON'T SHIP",
        "flipped_result": result(0.6),
        "changes": [{"to_label": "Exclude bots"}],
    }
    row = module.load(write(tmp_path, flip))
    assert row["ids"] == ["u_base", "u_near"]
    assert "Exclude bots: 0.6 [-0.4, 1.6], p 0.2, n 100, DON'T SHIP" in module.render([row])
