from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "adversary_ablation", ROOT / "scripts" / "adversary_ablation.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def option(oid: str, origin: str = "planner", default: bool = False) -> dict[str, Any]:
    return {"id": oid, "label": oid.upper(), "origin": origin, "is_default": default}


def universe(uid: str, model: str, cov: str, flipped: bool) -> dict[str, Any]:
    return {
        "id": uid,
        "choices": {"cov": cov, "model": model},
        "status": "done",
        "flipped": flipped,
        "verdict": "YES" if flipped else "NO",
    }


def run(universes: list[dict[str, Any]]) -> dict[str, Any]:
    steps = [
        {"id": "cov", "options": [option("c0", default=True), option("c1")]},
        {"id": "model", "options": [option("ols", default=True), option("nb", "adversary")]},
    ]
    return {
        "status": "completed",
        "case_id": "case",
        "plan": {"steps": steps},
        "garden": {"universes": {u["id"]: u for u in universes}},
        "report": {"original_verdict": "NO"},
    }


def test_an_adversary_option_whose_planner_twin_keeps_the_verdict_flips_alone() -> None:
    ablation = load()
    row = ablation.ablate_run(
        run(
            [
                universe("u0", "ols", "c0", False),
                universe("u1", "ols", "c1", False),
                universe("u2", "nb", "c0", True),
                universe("u3", "nb", "c1", True),
            ]
        )
    )
    assert row["planner_only_flips"] == 0 and row["adversary_flips"] == 2
    assert [f["option"] for f in row["adversary_alone"]] == ["NB", "NB"]
    summary = ablation.summarise([row])["case"]
    assert summary["only_the_adversary_finds_a_flip"] == 1


def test_a_flip_the_planner_twin_already_has_is_not_credited_to_the_adversary() -> None:
    ablation = load()
    row = ablation.ablate_run(
        run([universe("u1", "ols", "c1", True), universe("u3", "nb", "c1", True)])
    )
    assert row["planner_only_flips"] == 1
    assert row["adversary_alone"] == []
    assert ablation.summarise([row])["case"]["only_the_adversary_finds_a_flip"] == 0


def test_failed_runs_are_skipped() -> None:
    assert load().ablate_run({"status": "failed"}) is None


def test_the_markdown_lists_each_flip_the_adversary_found_alone() -> None:
    ablation = load()
    row = ablation.ablate_run(
        run([universe("u0", "ols", "c0", False), universe("u2", "nb", "c0", True)])
    )
    text = ablation.render(
        ablation.summarise([{**row, "file": "case-1.json"}]), [{**row, "file": "case-1.json"}], "T"
    )
    assert row["verdict"] == "NO"
    assert "| **all** | **1** | **1** | **0** | **1** | **1** | **1** |" in text
    assert "- `case-1.json` (NO): NB at `model` -> YES" in text
