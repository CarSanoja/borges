from __future__ import annotations

from pathlib import Path

from borges.evaluation.grid_borges import compare, recording_summary
from borges.evaluation.grid_plan import load_events, seeded_plan

CASES = Path(__file__).resolve().parents[2] / "cases"


def test_recording_summary_reads_the_committed_checkout_run() -> None:
    events = load_events(CASES / "checkout_ab" / "recorded" / "events.jsonl")
    summary = recording_summary(events, seeded_plan(events))
    assert summary["universes_used"] == 15
    assert summary["flip_found"] and summary["flip_n_changes"] == 1
    assert summary["flip_changes"] == ["internal_traffic=exclude_internal"]
    assert summary["flip_in_seeded_space"] is True
    assert summary["universes_from_adversary_options"] >= 1
    assert summary["wall_s"] > 0 and summary["llm_cost_usd"] == 0.0


def grid(found: bool, changes: list[str], robustness: float) -> dict:
    return {
        "smallest_flip": {"found": found, "n_changes": len(changes) or None, "changes": changes},
        "robustness": robustness,
        "universes_run": 100,
        "capped": False,
    }


def borges(found: bool, changes: list[str], robustness: float) -> dict:
    return {
        "flip_found": found,
        "flip_n_changes": len(changes) or None,
        "flip_changes": changes,
        "robustness_seeded_space_only": robustness,
        "universes_used": 10,
    }


def test_compare_reports_a_flip_the_search_missed() -> None:
    result = compare(grid(True, ["a=x"], 0.9), borges(False, [], 1.0))
    assert result["grid_found_flip_borges_missed"] is True
    assert result["same_smallest_flip"] is False
    assert result["universe_ratio_grid_over_borges"] == 10


def test_compare_reports_a_larger_borges_flip_and_the_robustness_gap() -> None:
    result = compare(grid(True, ["a=x"], 0.9), borges(True, ["a=x", "b=y"], 0.5))
    assert result["borges_flip_larger_than_grid_minimum_by"] == 1
    assert result["same_smallest_flip"] is False
    assert round(result["robustness_difference_borges_minus_grid"], 6) == -0.4


def test_compare_detects_the_same_flip() -> None:
    result = compare(grid(True, ["b=y", "a=x"], 0.9), borges(True, ["a=x", "b=y"], 0.9))
    assert result["same_smallest_flip"] is True
