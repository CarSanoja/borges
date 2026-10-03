from __future__ import annotations

from borges.config import Settings
from borges.llm.client import Role
from borges.llm.coder_model import nebius_role_models

Provider = str
DETERMINISTIC_MODEL = "deterministic"
SCRIPTED_MODEL = "scripted"


def model_for(role: Role, settings: Settings, provider: Provider = "nebius") -> str:
    if provider == "scripted":
        return SCRIPTED_MODEL
    if provider == "local":
        return settings.borges_local_model
    return nebius_role_models(settings.borges_coder_model)[role].id
