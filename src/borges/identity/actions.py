from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ActionRisk(StrEnum):
    PASSIVE = "passive"
    INTERNAL_MUTATION = "internal_mutation"
    EXTERNAL_MUTATION = "external_mutation"


class PermissionDecision(StrEnum):
    ALLOW = "allow"
    QUARANTINE = "quarantine"
    DENY = "deny"


class ToolAction(BaseModel):
    tool: str = Field(min_length=1)
    target: str = Field(min_length=1)
    risk: ActionRisk = ActionRisk.PASSIVE
    payload: dict[str, Any] = Field(default_factory=dict)


class PermissionVerdict(BaseModel):
    decision: PermissionDecision
    tool: str
    target: str
    reasons: list[str] = Field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.decision == PermissionDecision.ALLOW
