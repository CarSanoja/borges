from __future__ import annotations

from typing import Any

from borges.analysis.models import AnalysisPlan


def _seeded(plan: AnalysisPlan, choices: dict[str, str]) -> bool:
    return all(choices.get(step.id) in {o.id for o in step.options} for step in plan.steps)


def recording_summary(events: list[dict[str, Any]], plan: AnalysisPlan) -> dict[str, Any]:
    """What the committed bounded-search recording used and found, read from its events."""
    universes = {
        e["data"]["universe"]["id"]: e["data"]["universe"]
        for e in events
        if e.get("type") == "universe.finished"
    }
    done = [u for u in universes.values() if u["status"] == "done"]
    inside = [u for u in done if _seeded(plan, u["choices"])]
    report = next(e["data"]["report"] for e in events if e.get("type") == "report.ready")
    finished = next(e["data"] for e in events if e.get("type") == "run.finished")
    flip = report.get("minimal_flip")
    flipped_inside = [u for u in inside if u.get("flipped") is True]
    return {
        "universes_used": report["n_universes"],
        "n_flipped": report["n_flipped"],
        "robustness": report["robustness"],
        "universes_in_seeded_space": len(inside),
        "universes_from_adversary_options": len(done) - len(inside),
        "robustness_seeded_space_only": (
            (len(inside) - len(flipped_inside)) / len(inside) if inside else None
        ),
        "flip_found": flip is not None,
        "flip_n_changes": len(flip["changes"]) if flip else None,
        "flip_changes": [f"{c['step_id']}={c['to_option']}" for c in flip["changes"]]
        if flip
        else [],
        "flip_kind": flip.get("kind") if flip else None,
        "flip_in_seeded_space": bool(flip)
        and all(
            any(
                c["step_id"] == s.id and c["to_option"] in {o.id for o in s.options}
                for s in plan.steps
            )
            for c in flip["changes"]
        ),
        "wall_s": finished["elapsed_s"],
        "llm_cost_usd": 0.0,
    }


def compare(grid: dict[str, Any], borges: dict[str, Any]) -> dict[str, Any]:
    grid_flip = grid["smallest_flip"]
    gap = None
    if grid_flip["found"] and borges["flip_found"]:
        gap = borges["flip_n_changes"] - grid_flip["n_changes"]
    return {
        "grid_found_flip_borges_missed": grid_flip["found"] and not borges["flip_found"],
        "borges_flip_larger_than_grid_minimum_by": gap,
        "same_smallest_flip": grid_flip["found"]
        and borges["flip_found"]
        and sorted(grid_flip["changes"]) == sorted(borges["flip_changes"]),
        "robustness_difference_borges_minus_grid": (
            borges["robustness_seeded_space_only"] - grid["robustness"]
            if grid["robustness"] is not None and borges["robustness_seeded_space_only"] is not None
            else None
        ),
        "universe_ratio_grid_over_borges": grid["universes_run"] / borges["universes_used"],
        "grid_run_is_complete": not grid["capped"],
    }
