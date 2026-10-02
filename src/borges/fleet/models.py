from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class FieldSource(StrEnum):
    DECLARED = "declared"
    PROVIDER_CONFIG = "provider_config"
    PROMPT_TEXT = "prompt_text"
    OUTPUT_SCHEMA = "output_schema"
    SOURCE_CODE = "source_code"
    COMPUTED = "computed"


Lifecycle = Literal["active", "shadow", "retired"]
AgentKind = Literal["agent", "component"]
Approval = Literal["proposed", "approved", "retired"]
UseApproval = Literal["proposed", "approved", "retired", "unpublished"]


class AgentDescriptor(BaseModel):
    agent_id: str
    display_name: str
    purpose: str
    kind: AgentKind
    role: str
    model_id: str
    prompt_sha: str | None
    output_schema_sha: str | None
    code_sha: str | None
    capabilities: list[str]
    principal: str
    lifecycle: Lifecycle
    owner: str
    department: str
    definition_sha: str
    field_sources: dict[str, FieldSource] = Field(default_factory=dict)


class AgentUse(BaseModel):
    agent_id: str
    version: str | None
    definition_sha: str
    approval: UseApproval
    model_id: str
    prompt_sha: str | None = None
    principal: str
    lifecycle: Lifecycle


class RunAgents(BaseModel):
    registry_sha: str
    agents: list[AgentUse]
