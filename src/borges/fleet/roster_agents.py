from __future__ import annotations

from borges.analysis.schemas import (
    AdversaryOutput,
    CoderOutput,
    JudgeOutput,
    NarratorOutput,
    PlannerOutput,
    ReviewerOutput,
)
from borges.fleet.declarations import DEPARTMENT_ANALYSIS, AgentDeclaration
from borges.llm.client import Role

LLM_CAPS = ("spend.use",)
PROFILE = "dataset.profile.read"


def _agent(
    agent_id: str,
    name: str,
    purpose: str,
    role: Role,
    schema: type,
    capabilities: tuple[str, ...],
) -> AgentDeclaration:
    return AgentDeclaration(
        agent_id=agent_id,
        display_name=name,
        purpose=purpose,
        kind="agent",
        role=role.value,
        capabilities=capabilities,
        department=DEPARTMENT_ANALYSIS,
        llm_role=role,
        output_schema=schema,
    )


AGENT_DECLARATIONS: tuple[AgentDeclaration, ...] = (
    _agent(
        "planner",
        "Planner",
        "Designs the analysis as steps with defensible options from the dataset profile.",
        Role.PLANNER,
        PlannerOutput,
        (PROFILE, *LLM_CAPS),
    ),
    _agent(
        "coder",
        "Coder",
        "Writes the Python code of each analysis option against the plan contract.",
        Role.CODER,
        CoderOutput,
        (PROFILE, *LLM_CAPS),
    ),
    _agent(
        "repairer",
        "Repairer",
        "Rewrites option code that failed its smoke run, from the errors seen so far.",
        Role.REPAIRER,
        CoderOutput,
        (PROFILE, *LLM_CAPS),
    ),
    _agent(
        "adversary",
        "Adversary",
        "Proposes additional defensible options a skeptical reviewer would try.",
        Role.ADVERSARY,
        AdversaryOutput,
        (PROFILE, *LLM_CAPS),
    ),
    _agent(
        "judge",
        "Judge",
        "Scores how defensible each analysis option is, independently of its effect.",
        Role.JUDGE,
        JudgeOutput,
        (PROFILE, *LLM_CAPS),
    ),
    _agent(
        "reviewer",
        "Reviewer",
        "Checks that coded options are faithful to their spec and keep the estimand.",
        Role.REVIEWER,
        ReviewerOutput,
        (PROFILE, *LLM_CAPS),
    ),
    _agent(
        "narrator",
        "Narrator",
        "Writes the plain-language summary of the robustness report for a decision maker.",
        Role.NARRATOR,
        NarratorOutput,
        (*LLM_CAPS, "report.write"),
    ),
)
