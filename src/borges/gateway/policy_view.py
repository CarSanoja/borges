from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from borges.config import Settings
from borges.gateway.policy_load import LoadedPolicy, policy_for
from borges.gateway.policy_models import AgentPolicy, GatewayPolicy
from borges.telemetry.hashing import sha256_json


class AgentPolicyView(BaseModel):
    models: list[str]
    max_tokens: int
    max_calls_per_run: int
    max_cost_usd_per_run: float
    max_concurrent_calls: int
    egress: str
    max_sample_rows: int


class PolicyDocument(BaseModel):
    sha: str
    version: int
    description: str
    policy: GatewayPolicy


def agent_view(agent: AgentPolicy) -> AgentPolicyView:
    return AgentPolicyView(**agent.model_dump())


def policy_document(loaded: LoadedPolicy) -> PolicyDocument:
    return PolicyDocument(
        sha=loaded.sha,
        version=loaded.policy.version,
        description=loaded.policy.description,
        policy=loaded.policy,
    )


def effective_policy(settings: Settings) -> PolicyDocument:
    return policy_document(policy_for(settings))


def agent_policy_section(
    loaded: LoadedPolicy, agent_id: str, sandbox: bool
) -> dict[str, Any] | None:
    agent = loaded.agent(agent_id)
    policy = loaded.policy
    section: dict[str, Any] = {}
    if agent is not None:
        section.update(
            agent=agent.model_dump(mode="json"),
            retry=policy.retry.model_dump(),
            breaker=policy.breaker.model_dump(),
            run=policy.run.model_dump(),
        )
    if sandbox:
        section["sandbox"] = policy.sandbox.model_dump(mode="json")
    return section or None


def agent_policy_sha(settings: Settings, agent_id: str, sandbox: bool = False) -> str | None:
    section = agent_policy_section(policy_for(settings), agent_id, sandbox)
    return sha256_json(section) if section is not None else None
