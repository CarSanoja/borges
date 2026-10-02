from __future__ import annotations

from typing import Any

from borges.llm.client import ModelSpec, Role

LOCAL_LABEL = "Nemotron 3 Nano on Ollama (local, not Token Factory)"
THINKING_ROLES = frozenset({Role.PLANNER, Role.ADVERSARY, Role.JUDGE})


def local_role_models(
    model_id: str, thinking_roles: frozenset[Role] = THINKING_ROLES
) -> dict[Role, ModelSpec]:
    return {
        role: ModelSpec(
            id=model_id,
            input_usd_per_m=0.0,
            output_usd_per_m=0.0,
            thinking=role in thinking_roles,
        )
        for role in Role
    }


def ollama_thinking_body(enabled: bool) -> dict[str, Any]:
    return {} if enabled else {"reasoning_effort": "none"}
