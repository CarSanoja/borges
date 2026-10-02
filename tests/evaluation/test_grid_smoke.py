from __future__ import annotations

from pathlib import Path

from borges.evaluation.grid_plan import enumerate_grid
from borges.evaluation.grid_run import run_grid
from borges.evaluation.grid_stats import grid_summary
from borges.sandbox.local_backend import LocalBackend
from tests.evaluation.grid_support import small_plan


async def test_a_two_by_two_grid_runs_through_the_real_harness(tmp_path: Path) -> None:
    plan, data = small_plan()
    universes = enumerate_grid(plan)
    run = await run_grid(LocalBackend(tmp_path), plan, data, universes, concurrency=4)
    assert len(run.garden.universes) == 4
    summary = grid_summary(plan, run.garden, run.wall_s, 4, None, 0, run.checkpoints)
    assert summary["n_done"] == 4 and summary["n_failed"] == 0
    assert summary["baseline_verdict"] == "SHIP"
    assert summary["n_flipped"] == 2
    assert summary["robustness"] == 0.5
    assert summary["capped"] is False
    flip = summary["smallest_flip"]
    assert (
        flip["found"]
        and flip["n_changes"] == 1
        and flip["changes"] == ["internal=exclude_internal"]
    )
    assert summary["flips_by_n_changes"] == {"1": 1, "2": 1}


async def test_prefix_sharing_creates_fewer_checkpoints_than_from_scratch(tmp_path: Path) -> None:
    plan, data = small_plan()
    universes = enumerate_grid(plan)
    shared = await run_grid(LocalBackend(tmp_path / "a"), plan, data, universes, concurrency=1)
    scratch = await run_grid(
        LocalBackend(tmp_path / "b"), plan, data, universes, concurrency=1, reuse_prefixes=False
    )
    assert shared.checkpoints < scratch.checkpoints
    assert {u.id: u.verdict for u in shared.garden.universes.values()} == {
        u.id: u.verdict for u in scratch.garden.universes.values()
    }
