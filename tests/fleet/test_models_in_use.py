from __future__ import annotations

from borges.config import Settings
from borges.fleet.models_in_use import model_for
from borges.llm.client import DEFAULT_ROLE_MODELS, Role


def test_nebius_model_comes_from_the_provider_table() -> None:
    settings = Settings(_env_file=None)
    for role in Role:
        assert model_for(role, settings) == DEFAULT_ROLE_MODELS[role].id


def test_local_model_follows_settings() -> None:
    settings = Settings(_env_file=None, borges_local_model="custom:7b")
    assert model_for(Role.JUDGE, settings, "local") == "custom:7b"
    assert model_for(Role.JUDGE, settings, "scripted") == "scripted"
