from __future__ import annotations

from borges.garden.models import Universe
from borges.runtime.universe_checkpoint import (
    UNIVERSE_PREFIX,
    apply_options,
    load_restored,
    universe_key,
    universe_payload,
)
from tests.runs.fakes import make_plan


def finished(universe_id: str = "u_1", kind: str = "baseline") -> Universe:
    return Universe(
        id=universe_id,
        choices={"s1": "a", "s2": "x"},
        kind=kind,
        status="done",
        checkpoints=["cp1", "cp2"],
    )


def test_payload_carries_the_universe_the_options_it_used_and_the_root() -> None:
    plan = make_plan()
    payload = universe_payload(finished(), plan, "cp_root")
    assert payload["universe"]["id"] == "u_1" and payload["root_id"] == "cp_root"
    assert set(payload["options"]) == {"s1", "s2"}
    assert payload["options"]["s1"]["id"] == "a"
    assert universe_key("u_1") == f"{UNIVERSE_PREFIX}u_1"


def test_apply_options_puts_a_repaired_option_back_into_the_plan() -> None:
    plan = make_plan()
    payload = universe_payload(finished(), plan, "cp_root")
    payload["options"]["s1"]["code"] = "repaired"
    apply_options(plan, payload)
    assert plan.step("s1").option("a").code == "repaired"
    assert plan.step("s2").option("x").code is None


def test_apply_options_ignores_unknown_steps_and_options() -> None:
    plan = make_plan()
    payload = universe_payload(finished(), plan, None)
    payload["options"]["ghost"] = payload["options"]["s1"]
    payload["options"]["s2"]["id"] = "not-in-plan"
    apply_options(plan, payload)
    assert plan.step("s2").option("x").code is None


def test_load_restored_needs_a_baseline() -> None:
    plan = make_plan()
    baseline = ("universe:u_1", 5, universe_payload(finished(), plan, "cp_root"))
    single = (
        "universe:u_2",
        9,
        universe_payload(finished("u_2", "single"), plan, "cp_root"),
    )
    restored = load_restored([baseline, single])
    assert restored.order == ["u_1", "u_2"] and restored.ids == {"u_1", "u_2"}
    assert restored.baseline()["universe"]["id"] == "u_1"
    assert restored.universe("u_2").kind == "single"
    assert restored.checkpoint_ids() == {"cp1", "cp2", "cp_root"}
    assert bool(restored) is True
    assert not load_restored([single])
