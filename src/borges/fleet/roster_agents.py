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
    code_files: tuple[str, ...] = (),
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
        code_files=code_files,
    )


AGENT_DECLARATIONS: tuple[AgentDeclaration, ...] = (
    _agent(
        "planner",
        "Planner",
        "Designs the analysis as steps with defensible options from the dataset profile.",
        Role.PLANNER,
        PlannerOutput,
        (PROFILE, *LLM_CAPS),
        ("analysis/prompts/planner.py", "analysis/planner*.py"),
    ),
    _agent(
        "coder",
        "Coder",
        "Writes the Python code of each analysis option against the plan contract.",
        Role.CODER,
        CoderOutput,
        (PROFILE, *LLM_CAPS),
        ("analysis/prompts/coder*.py", "analysis/coder*.py", "analysis/model_spec/*.py"),
    ),
    _agent(
        "repairer",
        "Repairer",
        "Rewrites option code that failed its smoke run, from the errors seen so far.",
        Role.REPAIRER,
        CoderOutput,
        (PROFILE, *LLM_CAPS),
        ("analysis/prompts/coder*.py", "analysis/coder*.py"),
    ),
    _agent(
        "adversary",
        "Adversary",
        "Proposes additional defensible options a skeptical reviewer would try.",
        Role.ADVERSARY,
        AdversaryOutput,
        (PROFILE, *LLM_CAPS),
        ("analysis/prompts/adversary.py", "analysis/adversary.py", "runs/adversary_review.py"),
    ),
    _agent(
        "judge",
        "Judge",
        "Scores how defensible each analysis option is, independently of its effect.",
        Role.JUDGE,
        JudgeOutput,
        (PROFILE, *LLM_CAPS),
        ("analysis/prompts/judge.py", "analysis/judge.py"),
    ),
    _agent(
        "reviewer",
        "Reviewer",
        "Checks that coded options are faithful to their spec and keep the estimand.",
        Role.REVIEWER,
        ReviewerOutput,
        (PROFILE, *LLM_CAPS),
        ("analysis/prompts/reviewer.py", "analysis/smoke_review.py", "analysis/review_contract.py"),
    ),
    _agent(
        "narrator",
        "Narrator",
        "Writes the plain-language summary of the robustness report for a decision maker.",
        Role.NARRATOR,
        NarratorOutput,
        (*LLM_CAPS, "report.write"),
        ("analysis/prompts/narrator.py", "analysis/narrat*.py"),
    ),
)
