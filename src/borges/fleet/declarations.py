from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from borges.fleet.models import AgentKind, Lifecycle
from borges.llm.client import Role

OWNER = "borges-core"
DEPARTMENT_ANALYSIS = "decision-analytics"
DEPARTMENT_ASSURANCE = "analysis-assurance"


@dataclass(frozen=True)
class AgentDeclaration:
    agent_id: str
    display_name: str
    purpose: str
    kind: AgentKind
    role: str
    capabilities: tuple[str, ...]
    department: str
    llm_role: Role | None = None
    output_schema: type[BaseModel] | None = None
    code_files: tuple[str, ...] = field(default_factory=tuple)
    lifecycle: Lifecycle = "active"
    owner: str = OWNER
