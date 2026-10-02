from __future__ import annotations

import pytest

from borges.garden.models import Universe
from borges.runtime.alias_backend import AliasBackend
from borges.runtime.baseline_restore import ResumeError
from borges.runtime.restore_search import restore_search
from borges.runtime.universe_checkpoint import RestoredUniverses, universe_payload
from tests.runs.fakes import make_plan
from tests.runtime.test_alias_backend import Inner
from tests.runtime.test_baseline_restore import FakeExecutor


def universe(universe_id: str, kind: str, choices: dict[str, str]) -> Universe:
    return Universe(
        id=universe_id, choices=choices, kind=kind, status="done", checkpoints=["c1", "c2"]
    )


async def test_every_restored_universe_puts_its_repaired_options_back() -> None:
    plan = make_plan()
    restored = RestoredUniverses()
    base = universe_payload(universe("u_b", "baseline", {"s1": "a", "s2": "x"}), plan, "root")
    other = universe_payload(universe("u_s", "single", {"s1": "b", "s2": "x"}), plan, "root")
    other["options"]["s1"]["code"] = "fixed"
    for key, value in (("u_b", base), ("u_s", other)):
        restored.payloads[key] = value
        restored.order.append(key)
    await restore_search(FakeExecutor(), AliasBackend(Inner()), plan, restored)
    assert plan.step("s1").option("b").code == "fixed"


async def test_nothing_to_restore_is_an_error() -> None:
    with pytest.raises(ResumeError):
        await restore_search(
            FakeExecutor(), AliasBackend(Inner()), make_plan(), RestoredUniverses()
        )
