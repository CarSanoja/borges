from __future__ import annotations

import pytest

from borges.garden.search import minimal_flip
from borges.garden.verify import verify_flip
from tests.garden import fakes
from tests.garden.fakes import FakeBackend, build_garden, install_fake_harness, make_plan


@pytest.fixture(autouse=True)
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_harness(monkeypatch)


async def test_verify_flip_reproduces_in_fresh_chain() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    _, garden = await build_garden(plan, backend)
    flip = minimal_flip(plan, garden)
    assert flip is not None
    runs_before = len(backend.runs)
    verified = await verify_flip(backend, plan, b"data", flip, garden)
    assert len(backend.runs) - runs_before == 6
    assert backend.root_calls == 2
    assert verified.reproduced is True
    assert verified.reproduce_command is not None
    assert verified.reproduce_command.startswith("from checkpoint cp")
    assert verified.reproduce_command.endswith("python s1:a && python s2:x && python s3:o")
    assert flip.reproduced is None
    assert verified.universe_id == flip.universe_id


async def test_verify_flip_detects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    _, garden = await build_garden(plan, backend)
    flip = minimal_flip(plan, garden)
    assert flip is not None
    monkeypatch.setitem(fakes.EFFECTS, ("s3", "o"), -2.5)
    verified = await verify_flip(backend, plan, b"data", flip, garden)
    assert verified.reproduced is False


async def test_verify_flip_reports_failure_as_not_reproduced() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    _, garden = await build_garden(plan, backend)
    flip = minimal_flip(plan, garden)
    assert flip is not None
    backend.fail = {("s3", "o")}
    verified = await verify_flip(backend, plan, b"data", flip, garden)
    assert verified.reproduced is False


async def test_verify_flip_detects_baseline_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    _, garden = await build_garden(plan, backend)
    flip = minimal_flip(plan, garden)
    assert flip is not None
    monkeypatch.setitem(fakes.EFFECTS, ("s1", "a"), 5.0)
    verified = await verify_flip(backend, plan, b"data", flip, garden)
    assert verified.reproduced is False


async def test_verify_flip_requires_differing_verdicts() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    _, garden = await build_garden(plan, backend)
    flip = minimal_flip(plan, garden)
    assert flip is not None
    same = flip.model_copy(update={"flipped_verdict": flip.baseline_verdict})
    verified = await verify_flip(backend, plan, b"data", same, garden)
    assert verified.reproduced is False
