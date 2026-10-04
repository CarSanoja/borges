from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "repeats_report", ROOT / "scripts" / "repeats_report.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(status: str, flip_to: str | None = None, origin: str = "planner") -> dict[str, Any]:
    changes = [{"to_option": "o1"}] if flip_to else []
    return {
        "status": status,
        "run_id": f"r_{status}_{flip_to}",
        "error": None if status == "completed" else "LLMError: boom",
        "plan": {"steps": [{"id": "s", "options": [{"id": "o1", "origin": origin}]}]},
        "report": {
            "original_verdict": "SHIP",
            "minimal_flip": {"changes": changes},
            "n_universes": 10,
            "n_failed": 1,
            "coding": {"repaired_after_smoke": 2},
        }
        if status == "completed"
        else None,
        "usage": {"cost_usd": 0.02},
    }


def test_wilson_matches_the_textbook_interval() -> None:
    low, high = load().wilson(33, 35)
    assert low == pytest.approx(0.8139, abs=1e-3) and high == pytest.approx(0.9842, abs=1e-3)


def test_the_report_counts_completions_flips_and_failures(tmp_path: Path) -> None:
    runs = [run("completed", "x", "adversary"), run("completed"), run("failed")]
    for i, body in enumerate(runs, start=1):
        (tmp_path / f"case_a-{i}.json").write_text(json.dumps(body))
    (tmp_path / "case_a-4.json").write_text("{not json")
    module = load()
    text = module.render(module.load_batch(tmp_path), "abc1234", "2026-10-04")
    assert "**Runs completed: 2 of 4**" in text
    assert "| case_a | 2/4 | SHIP ×2 | 1/2 | 50%" in text
    assert "| 1 | 20 (2) | $0.020 |" in text
    assert "options repaired after the smoke stage: 4" in text
    assert "LLMError: boom" in text and "unreadable JSON" in text
