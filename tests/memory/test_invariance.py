from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from borges.runs.models import RunSnapshot
from tests.memory.counting import Bench, settings_for

pytestmark = pytest.mark.timeout(900)

CASES = {
    "checkout_ab": (15, 5),
    "red_cards": (41, 5),
    "marp_norms": (27, 1),
    "marp_religiosity": (40, 0),
}
VOLATILE = {
    "started_at",
    "finished_at",
    "duration_s",
    "elapsed_s",
    "created_at",
    "ts",
    "checkpoints",
}


def strip(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [strip(v) for v in value]
    return value


def table(snapshot: RunSnapshot) -> dict[str, Any]:
    universes = {
        uid: strip(universe.model_dump(mode="json"))
        for uid, universe in sorted(snapshot.garden.universes.items())
    }
    flip = snapshot.flip
    report = snapshot.report
    return {
        "universes": universes,
        "flip": flip.universe_id if flip else None,
        "verdict": report.original_verdict if report else None,
    }


@pytest.mark.parametrize("case", sorted(CASES))
async def test_memory_never_changes_a_universe(tmp_path: Path, case: str) -> None:
    total, flipped = CASES[case]
    off = Bench(settings_for(tmp_path / "off", borges_memory=False))
    on = Bench(settings_for(tmp_path / "on", borges_memory=True))
    (baseline, _), (first, _) = await asyncio.gather(
        off.run("r_off", case=case), on.run("r_one", case=case)
    )
    second, second_calls = await on.run("r_two", case=case)

    assert len(baseline.garden.universes) == total
    assert sum(1 for u in baseline.garden.universes.values() if u.flipped) == flipped
    assert table(first) == table(baseline)
    assert table(second) == table(baseline)
    assert baseline.memory is None and second.memory is not None
    assert sum(second.memory.reused.values()) > 0
