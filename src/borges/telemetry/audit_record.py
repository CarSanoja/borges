from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from borges.telemetry.hashing import canonical_json, sha256_text

GENESIS_HASH = "0" * 64
SCHEMA_VERSION = 1

Decision = Literal["allow", "deny", "observe"]


class AuditRecord(BaseModel):
    v: int = SCHEMA_VERSION
    seq: int
    ts: str
    kind: str
    run_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    principal: str | None = None
    decision: Decision | None = None
    reason: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str = GENESIS_HASH
    hash: str = ""

    def body(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"hash"})

    def seal(self) -> AuditRecord:
        return self.model_copy(update={"hash": sha256_text(canonical_json(self.body()))})

    def line(self) -> str:
        return canonical_json(self.model_dump(mode="json"))
