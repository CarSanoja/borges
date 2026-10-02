from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from borges.fleet.models import Approval

BumpKind = str


class Transition(BaseModel):
    ts: float
    state: Approval
    by: str
    reason: str | None = None


class VersionRecord(BaseModel):
    agent_id: str
    version: str
    definition_sha: str
    state: Approval
    bump: BumpKind
    changelog: str
    published_at: float
    published_by: str
    descriptor: dict[str, Any]
    history: list[Transition] = Field(default_factory=list)


def parse_version(version: str) -> tuple[int, int, int]:
    major, minor, patch = (int(part) for part in version.split("."))
    return major, minor, patch


def format_version(parts: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in parts)
