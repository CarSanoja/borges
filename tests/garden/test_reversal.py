from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest

from borges.garden.executor import GardenExecutor
from borges.garden.influence import build_report
from borges.garden.models import Garden
from borges.garden.reversal import REVERSED_REASON
from borges.garden.search import minimal_flip
from borges.sandbox.backend import Checkpoint
from tests.garden import fakes
from tests.garden.fakes import FakeBackend, install_fake_harness, make_plan

ROWS = 60


def _frame(values: np.ndarray, extra: str = "score") -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame({"y": np.arange(ROWS), extra: values}).to_parquet(buffer)
    return buffer.getvalue()


class FrameBackend(FakeBackend):
    def __init__(self, plan, frames):
        super().__init__(plan)
        self.frames = frames

    async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes:
        chosen = self._choices[checkpoint.id]
        if not chosen:
            raise FileNotFoundError(path)
        step_id = list(chosen)[-1]
        return self.frames.get((step_id, chosen[step_id]), _frame(np.arange(ROWS) * 1.0))


async def _garden(plan, backend):
    executor = GardenExecutor(backend, plan, b"data")
    await executor.setup()
    garden = Garden()
    base = await executor.run_universe(plan.default_choices(), "baseline")
    garden.add(base)
    garden.baseline_id = base.id
    return executor, garden


@pytest.fixture(autouse=True)
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_harness(monkeypatch)


def _transform_plan():
    plan = make_plan()
    plan.steps[1].produces = ["score"]
    return plan


async def test_agreeing_transform_is_still_a_flip() -> None:
    plan = _transform_plan()
    values = np.arange(ROWS) * 1.0
    frames = {("s2", "x"): _frame(values), ("s2", "y"): _frame(values / 7 + 3)}
    executor, garden = await _garden(plan, FrameBackend(plan, frames))
    universe = await executor.run_universe({"s2": "y"}, "single")
    garden.add(universe)
    assert universe.status == "done"
    assert universe.flipped is True
    assert minimal_flip(plan, garden) is not None


async def test_sign_flipped_transform_is_not_a_flip() -> None:
    plan = _transform_plan()
    values = np.arange(ROWS) * 1.0
    frames = {("s2", "x"): _frame(values), ("s2", "y"): _frame(-values)}
    executor, garden = await _garden(plan, FrameBackend(plan, frames))
    universe = await executor.run_universe({"s2": "y"}, "single")
    garden.add(universe)
    assert universe.status == "failed"
    assert universe.flipped is None
    assert universe.error is not None
    assert universe.error.startswith(REVERSED_REASON)
    assert "column 'score' correlates -1.00" in universe.error
    assert minimal_flip(plan, garden) is None
    report = build_report(plan, garden, None)
    assert any("reverses a variable's direction" in c for c in report.caveats)


async def test_unnamed_columns_are_compared_when_produces_is_empty() -> None:
    plan = make_plan()
    values = np.arange(ROWS) * 1.0
    frames = {("s2", "x"): _frame(values), ("s2", "y"): _frame(-values)}
    executor, _ = await _garden(plan, FrameBackend(plan, frames))
    universe = await executor.run_universe({"s2": "y"}, "single")
    assert universe.status == "done"

    class Adding(FrameBackend):
        async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes:
            chosen = self._choices[checkpoint.id]
            if "s2" not in chosen:
                return _frame(values, "other")
            return await super().read_file(checkpoint, path)

    backend = Adding(plan, frames)
    executor, _ = await _garden(plan, backend)
    universe = await executor.run_universe({"s2": "y"}, "single")
    assert universe.status == "failed"
    assert "'score'" in (universe.error or "")


async def test_filter_flip_is_unaffected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(fakes.EFFECTS, ("s1", "b"), -1.5)
    plan = _transform_plan()
    values = np.arange(ROWS) * 1.0
    frames = {("s1", "b"): _frame(-values), ("s2", "x"): _frame(values)}
    executor, garden = await _garden(plan, FrameBackend(plan, frames))
    universe = await executor.run_universe({"s1": "b"}, "single")
    assert universe.status == "done"
    assert universe.flipped is True


async def test_short_overlap_is_skipped() -> None:
    plan = _transform_plan()
    buffer = io.BytesIO()
    pd.DataFrame({"score": [1.0, 2.0, 3.0]}).to_parquet(buffer)
    small = buffer.getvalue()
    frames = {("s2", "x"): _frame(np.arange(ROWS) * 1.0), ("s2", "y"): small}
    executor, _ = await _garden(plan, FrameBackend(plan, frames))
    universe = await executor.run_universe({"s2": "y"}, "single")
    assert universe.status == "done"
