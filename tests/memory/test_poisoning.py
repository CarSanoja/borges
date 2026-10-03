from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.config import Settings
from borges.memory import service
from borges.memory.kinds import MemoryKind
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path
from tests.memory.counting import Bench, settings_for
from tests.memory.plans import profile
from tests.memory.poisoned_bench import ATTACK, poison_rows, recording_bench
from tests.memory.sessions import make_session

pytestmark = pytest.mark.timeout(400)


async def test_poisoned_memories_never_reach_a_prompt_and_are_audited(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, borges_memory=True)
    clean = Bench(settings)
    await clean.run("r_one")
    changed = poison_rows(settings)
    assert changed["verdict"] > 0 and changed["adversary"] > 0

    seen: list[str] = []
    bench = recording_bench(settings, seen)
    snapshot, _ = await bench.run("r_two")

    assert snapshot.status == "completed"
    assert seen and not any(ATTACK in text or "Ignore all previous" in text for text in seen)
    assert snapshot.memory is not None and snapshot.memory.dropped >= 3
    screened = [r for r in read_records(global_audit_path(settings)) if r.kind == "memory.screened"]
    kinds = {r.data["memory_kind"] for r in screened}
    assert {"verdict", "adversary", "note"} <= kinds
    assert all(r.data["stage"] == "read" and r.decision == "deny" for r in screened)
    assert ATTACK not in json.dumps([r.model_dump(mode="json") for r in screened])


def test_the_normal_write_path_refuses_and_audits_poison(settings: Settings) -> None:
    session = make_session(settings, run_id="r_old")
    session.attach(profile())
    assert session.stage(MemoryKind.VERDICT, "v", {"reason": ATTACK, "text": "t"}) is False
    assert (
        session.stage(
            MemoryKind.ADVERSARY,
            "a",
            {"label": "x", "spec": "y", "reason": ATTACK, "why": "rejected"},
        )
        is False
    )
    with pytest.raises(ValueError, match="instruction"):
        service.add_note(settings, "caller://acme", "acme", "a" * 64, "amount", ATTACK)
    rows = [r for r in read_records(global_audit_path(settings)) if r.kind == "memory.screened"]
    assert [r.data["memory_kind"] for r in rows] == ["verdict", "adversary", "note"]
    assert all(r.data["stage"] == "write" and r.data["tenant"] == "acme" for r in rows)
    assert ATTACK not in json.dumps([r.model_dump(mode="json") for r in rows])
