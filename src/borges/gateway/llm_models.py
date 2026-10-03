from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from borges.gateway.policy_models import AgentPolicy
from borges.llm.client import KNOWN_MODELS, LLMClient, ModelSpec, Role

SCRIPTED = "scripted"


@dataclass(frozen=True)
class ModelChain:
    models: list[str]
    auth_target: str
    substitute: bool


def requested_model(inner: LLMClient, role: Role) -> str:
    models = getattr(inner, "role_models", None)
    spec = models.get(role) if isinstance(models, dict) else None
    return spec.id if spec is not None else SCRIPTED


def resolve_spec(inner: LLMClient, model: str) -> ModelSpec | None:
    models = getattr(inner, "role_models", None)
    if isinstance(models, dict):
        for spec in models.values():
            if getattr(spec, "id", None) == model and hasattr(spec, "cost"):
                return spec
    return KNOWN_MODELS.get(model)


def build_chain(agent: AgentPolicy, requested: str, local_model: str | None) -> ModelChain | None:
    if requested in agent.models:
        return ModelChain(agent.models[agent.models.index(requested) :], requested, False)
    if requested in agent.alternatives:
        return ModelChain([requested], requested, False)
    if requested == SCRIPTED or (local_model is not None and requested == local_model):
        return ModelChain([requested], agent.primary, True)
    return None


def estimate_cost(spec: Any, prompt_tokens: int, max_tokens: int) -> float:
    return float(spec.cost(prompt_tokens, max_tokens)) if spec is not None else 0.0
