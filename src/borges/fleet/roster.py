from __future__ import annotations

from borges.fleet.declarations import AgentDeclaration
from borges.fleet.roster_agents import AGENT_DECLARATIONS
from borges.fleet.roster_components import COMPONENT_DECLARATIONS

ROSTER: tuple[AgentDeclaration, ...] = (*AGENT_DECLARATIONS, *COMPONENT_DECLARATIONS)


def declaration_for(agent_id: str) -> AgentDeclaration | None:
    return next((item for item in ROSTER if item.agent_id == agent_id), None)
