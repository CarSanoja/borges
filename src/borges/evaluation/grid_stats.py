from __future__ import annotations

from typing import Any

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden
from borges.garden.search import changes_for, minimal_flip


def flip_summary(plan: AnalysisPlan, garden: Garden) -> dict[str, Any]:
    flip = minimal_flip(plan, garden)
    if flip is None:
        return {"found": False, "n_changes": None, "changes": [], "kind": None}
    return {
        "found": True,
        "n_changes": len(flip.changes),
        "changes": [f"{c.step_id}={c.to_option}" for c in flip.changes],
        "kind": flip.kind,
        "baseline_estimate": flip.baseline_result.estimate,
        "flipped_estimate": flip.flipped_result.estimate,
        "flipped_verdict": flip.flipped_verdict,
    }


def flip_size_histogram(plan: AnalysisPlan, garden: Garden) -> dict[str, int]:
    histogram: dict[str, int] = {}
    for universe in garden.finished():
        if universe.flipped is True:
            key = str(len(changes_for(plan, universe.choices)))
            histogram[key] = histogram.get(key, 0) + 1
    return dict(sorted(histogram.items(), key=lambda item: int(item[0])))


def grid_summary(
    plan: AnalysisPlan,
    garden: Garden,
    wall_s: float,
    grid_total: int,
    cap: int | None,
    seed: int,
    checkpoints: int,
) -> dict[str, Any]:
    finished = garden.finished()
    flipped = [u for u in finished if u.flipped is True]
    failed = [u for u in garden.universes.values() if u.status == "failed"]
    n = len(finished)
    baseline = garden.baseline
    estimates = [u.result.estimate for u in finished if u.result is not None]
    return {
        "grid_size": grid_total,
        "universes_run": len(garden.universes),
        "capped": len(garden.universes) < grid_total,
        "cap": cap,
        "seed": seed,
        "n_done": n,
        "n_failed": len(failed),
        "n_flipped": len(flipped),
        "robustness": (n - len(flipped)) / n if n else None,
        "baseline_verdict": baseline.verdict if baseline else None,
        "estimate_min": min(estimates) if estimates else None,
        "estimate_max": max(estimates) if estimates else None,
        "smallest_flip": flip_summary(plan, garden),
        "flips_by_n_changes": flip_size_histogram(plan, garden),
        "wall_s": wall_s,
        "checkpoints": checkpoints,
    }
