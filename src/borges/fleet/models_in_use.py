from __future__ import annotations

from borges.config import Settings
from borges.llm.client import DEFAULT_ROLE_MODELS, Role

Provider = str
DETERMINISTIC_MODEL = "deterministic"
SCRIPTED_MODEL = "scripted"


def model_for(role: Role, settings: Settings, provider: Provider = "nebius") -> str:
    if provider == "scripted":
        return SCRIPTED_MODEL
    if provider == "local":
        return settings.borges_local_model
    return DEFAULT_ROLE_MODELS[role].id
