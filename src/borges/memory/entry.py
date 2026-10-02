from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from borges.memory.kinds import MemoryKind


@dataclass
class MemoryEntry:
    kind: MemoryKind
    dataset_fp: str
    family_fp: str
    signature: str
    payload: dict[str, Any]
    run_id: str = ""
    agent_id: str | None = None
    agent_version: str | None = None
    definition_sha: str | None = None
    created_at: float = 0.0
    last_used_at: float = 0.0
    hits: int = 0
    row_id: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return str(self.payload.get("text", ""))
