from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from borges.identity.actions import PermissionDecision


class AuthorizationRecord(BaseModel):
    recorded_at: str
    agent_id: str
    principal_id: str
    tool: str
    target: str
    capability: str
    decision: str
    reasons: list[str] = Field(default_factory=list)


@dataclass
class CapabilityLedger:
    parent: CapabilityLedger | None = None
    records: list[AuthorizationRecord] = field(default_factory=list)

    def add(self, record: AuthorizationRecord) -> None:
        self.records.append(record)
        if self.parent is not None:
            self.parent.add(record)

    @property
    def denials(self) -> list[AuthorizationRecord]:
        return [r for r in self.records if r.decision == PermissionDecision.DENY.value]


_LEDGER: ContextVar[CapabilityLedger | None] = ContextVar("borges_capability_ledger", default=None)


@contextmanager
def capability_scope() -> Iterator[CapabilityLedger]:
    ledger = CapabilityLedger(parent=_LEDGER.get())
    token = _LEDGER.set(ledger)
    try:
        yield ledger
    finally:
        _LEDGER.reset(token)


def add_to_current_ledger(record: AuthorizationRecord) -> None:
    ledger = _LEDGER.get()
    if ledger is not None:
        ledger.add(record)
