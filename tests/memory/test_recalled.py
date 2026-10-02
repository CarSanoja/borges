from __future__ import annotations

from borges.memory.entry import MemoryEntry
from borges.memory.kinds import MemoryKind
from borges.memory.recalled import Recalled


def test_recalled_exposes_payload_and_source_run() -> None:
    entry = MemoryEntry(MemoryKind.CODE, "d", "f", "s", {"code": "x"}, run_id="r_1")
    recalled = Recalled(entry, "exact")
    assert recalled.payload == {"code": "x"}
    assert recalled.run_id == "r_1"
    assert recalled.score == 1.0
