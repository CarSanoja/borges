from __future__ import annotations

from typing import Any

import pytest

from borges.garden.models import Universe
from borges.garden.prefix_cache import PrefixCache, PrefixNode
from borges.runtime.alias_backend import AliasBackend
from borges.runtime.baseline_restore import ResumeError, restore_baseline
from borges.runtime.universe_checkpoint import universe_payload
from borges.sandbox.backend import Checkpoint
from tests.runs.fakes import make_plan
from tests.runtime.test_alias_backend import Inner


class FakeExecutor:
    def __init__(self, fail_at: int | None = None) -> None:
        self.data = b"rows"
        self.emit: Any = "original"
        self.root = None
        self.fail_at = fail_at
        self.computed: list[tuple[str, str]] = []
        self.emit_during: list[Any] = []
        self._cache = PrefixCache()
        self.baseline_verdict = None
        self.baseline_result = None
        self.baseline_checkpoints: list[str] = []

    async def _compute_prefix(self, parent, index, step_id, option_id):
        self.computed.append((step_id, option_id))
        self.emit_during.append(self.emit)
        if index == self.fail_at:
            return PrefixNode(None, error="sandbox down")
        return PrefixNode(Checkpoint(f"new_{index}", parent.id, "inner"))


def payload(root: str | None = "old_root") -> dict:
    baseline = Universe(
        id="u_base",
        choices={"s1": "a", "s2": "x"},
        kind="baseline",
        status="done",
        verdict="ship",
        checkpoints=["old_1", "old_2"],
    )
    return universe_payload(baseline, make_plan(), root)


async def test_rebuild_keeps_recorded_ids_and_mutes_events() -> None:
    executor, backend, plan = FakeExecutor(), AliasBackend(Inner()), make_plan()
    baseline = await restore_baseline(executor, backend, plan, payload())
    assert baseline.id == "u_base"
    assert executor.computed == [("s1", "a"), ("s2", "x")]
    assert executor.emit_during == [None, None] and executor.emit == "original"
    assert executor.root.id == "old_root"
    assert backend.aliases["old_root"].id == "real_root"
    assert backend.aliases["old_1"].id == "new_0" and backend.aliases["old_2"].id == "new_1"
    assert executor.baseline_checkpoints == ["old_1", "old_2"]
    assert executor.baseline_verdict == "ship"
    seeded = list(executor._cache._nodes.values())
    assert [n.checkpoint.id for n in seeded] == ["old_1", "old_2"]
    assert seeded[1].checkpoint.parent_id == "old_1"


async def test_a_baseline_that_cannot_be_rebuilt_fails_the_resume() -> None:
    executor = FakeExecutor(fail_at=1)
    with pytest.raises(ResumeError, match="sandbox down"):
        await restore_baseline(executor, AliasBackend(Inner()), make_plan(), payload())
    assert executor.emit == "original"


async def test_a_checkpoint_without_a_root_is_refused() -> None:
    with pytest.raises(ResumeError, match="root"):
        await restore_baseline(FakeExecutor(), AliasBackend(Inner()), make_plan(), payload(None))
