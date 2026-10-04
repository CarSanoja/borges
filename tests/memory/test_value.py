from __future__ import annotations

from pathlib import Path

import pytest

from borges.fleet.fleet import build_fleet
from borges.fleet.locations import open_store
from borges.runs.models import RunSnapshot
from tests.memory.counting import Bench, settings_for

pytestmark = pytest.mark.timeout(400)
KEY = "v" * 32


def outcome(snapshot: RunSnapshot) -> tuple:
    flip = snapshot.flip
    estimates = {
        uid: (u.result.estimate, u.result.p_value, u.verdict)
        for uid, u in snapshot.garden.universes.items()
        if u.result
    }
    report = snapshot.report
    return (
        sorted(snapshot.garden.universes),
        flip.universe_id if flip else None,
        flip.flipped_verdict if flip else None,
        estimates,
        report.original_verdict if report else None,
    )


async def test_second_run_makes_fewer_judge_and_coder_calls_with_the_same_result(
    tmp_path: Path,
) -> None:
    plain = Bench(settings_for(tmp_path / "off", borges_memory=False))
    baseline, baseline_calls = await plain.run("r_off")
    bench = Bench(settings_for(tmp_path / "on", borges_memory=True))
    first, first_calls = await bench.run("r_one")
    second, second_calls = await bench.run("r_two")

    assert baseline.status == first.status == second.status == "completed"
    assert baseline.flip is not None and baseline.flip.universe_id == "u_4e00fbb461"
    assert len(baseline.garden.universes) == 15
    assert outcome(first) == outcome(baseline)
    assert outcome(second) == outcome(baseline)
    assert baseline.memory is None
    assert first.memory is not None and first.memory.reused == {}
    assert first.memory.stored == {"verdict": 7, "code": 11, "adversary": 1}

    assert first_calls["judge"] == baseline_calls["judge"] == 7
    assert first_calls["coder"] == baseline_calls["coder"] == 14
    assert second_calls["judge"] < first_calls["judge"]
    assert second_calls["coder"] < first_calls["coder"]
    assert second_calls["planner"] == first_calls["planner"]
    print(
        "memory value on checkout_ab: judge",
        first_calls["judge"],
        "->",
        second_calls["judge"],
        "coder",
        first_calls["coder"],
        "->",
        second_calls["coder"],
    )

    assert second.memory is not None
    assert second.memory.mode == "public-demo" and second.memory.encrypted is False
    assert second.memory.sources[0].run_id == "r_one"
    assert sum(second.memory.reused.values()) >= 18
    assert [e.type for e in bench.store.events("r_two")].count("memory.used") == 1


async def test_a_retired_judge_version_is_not_trusted(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, borges_memory=True)
    bench = Bench(settings)
    first, first_calls = await bench.run("r_one", max_universes=3)
    judge = build_fleet(settings).get("judge")
    store = open_store(settings)
    record = store.by_definition("judge", judge.definition_sha)
    store.transition("judge", record.version, "retired", "tester", "superseded")
    second, second_calls = await bench.run("r_two", max_universes=3)
    assert second_calls["judge"] == first_calls["judge"] > 0
    assert second_calls["coder"] < first_calls["coder"]
    assert outcome(first) == outcome(second)


async def test_named_tenants_do_not_share_memory_and_need_the_key(tmp_path: Path) -> None:
    keyed = Bench(settings_for(tmp_path / "k", borges_memory=True, borges_memory_key=KEY))
    one, one_calls = await keyed.run("r_a1", principal="caller://acme", max_universes=3)
    other, other_calls = await keyed.run("r_b1", principal="caller://bob", max_universes=3)
    again, again_calls = await keyed.run("r_a2", principal="caller://acme", max_universes=3)
    assert other_calls["judge"] == one_calls["judge"] and other.memory.reused == {}
    assert again_calls["judge"] == 0
    assert 0 < again_calls["coder"] < one_calls["coder"]
    assert again.memory.sources[0].run_id == "r_a1"
    assert outcome(one) == outcome(other) == outcome(again)

    keyless = Bench(settings_for(tmp_path / "n", borges_memory=True))
    _, first_calls = await keyless.run("r_n1", principal="caller://acme", max_universes=3)
    _, second_calls = await keyless.run("r_n2", principal="caller://acme", max_universes=3)
    assert second_calls["judge"] == first_calls["judge"] > 0
    assert not (tmp_path / "n" / "home" / "memory").exists()
