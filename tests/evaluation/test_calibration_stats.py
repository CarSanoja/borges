from __future__ import annotations

import pytest

from borges.evaluation.calibration_grid import build_jobs, full_cells, smoke_cells
from borges.evaluation.calibration_stats import summarise, wilson


def test_wilson_known_values() -> None:
    p, low, high = wilson(50, 100)
    assert p == 0.5
    assert low == pytest.approx(0.404, abs=0.002)
    assert high == pytest.approx(0.596, abs=0.002)
    assert wilson(0, 80)[1] == 0.0
    assert wilson(0, 80)[2] < 0.05


def test_summarise_counts_flips_and_kinds() -> None:
    base = {"cell": "c", "n_changes": 1, "seconds": 1.0, "flip_steps": []}
    rows = [
        {
            **base,
            "seed": 1,
            "original_verdict": "SHIP",
            "flip_found": True,
            "flip_kind": "direction",
            "flip_steps": ["internal_traffic"],
        },
        {**base, "seed": 2, "original_verdict": "SHIP", "flip_found": False, "flip_kind": None},
        {
            **base,
            "seed": 3,
            "original_verdict": "DON'T SHIP",
            "flip_found": True,
            "flip_kind": "significance",
        },
    ]
    cell = summarise(rows, {"c": 3})["c"]
    assert cell["flip_any"]["k"] == 2
    assert cell["flip_given_ship"]["k"] == 1 and cell["flip_given_ship"]["n"] == 2
    assert cell["flip_via_internal_traffic"]["k"] == 1
    assert cell["flip_direction"]["k"] == 1 and cell["flip_direction"]["n"] == 3
    assert cell["flip_kinds"] == {"direction": 1, "significance": 1}


def test_grid_jobs_are_seeded_and_unique() -> None:
    jobs, scanned = build_jobs(smoke_cells())
    assert len(jobs) == 2 and len({(j.cell.key, j.seed) for j in jobs}) == 2
    again, _ = build_jobs(smoke_cells())
    assert [j.seed for j in jobs] == [j.seed for j in again]
    assert sum(c.replicates for c in full_cells()) >= 400
