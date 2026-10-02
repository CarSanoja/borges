from __future__ import annotations

from borges.memory.entry import MemoryEntry
from borges.memory.kinds import MemoryKind


def test_text_reads_the_payload() -> None:
    entry = MemoryEntry(MemoryKind.NOTE, "d", "f", "s", {"text": "hello"})
    assert entry.text == "hello"
    assert MemoryEntry(MemoryKind.NOTE, "d", "f", "s", {}).text == ""
