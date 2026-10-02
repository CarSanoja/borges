from __future__ import annotations

import pytest

from borges.analysis.prompts import judge
from borges.config import Settings
from borges.fleet.descriptor import build_descriptor
from borges.fleet.models import FieldSource
from borges.fleet.roster import declaration_for
from borges.llm.client import DEFAULT_ROLE_MODELS, SUPER, Role


def describe(settings: Settings, agent_id: str, provider: str = "nebius"):
    declaration = declaration_for(agent_id)
    assert declaration is not None
    return build_descriptor(declaration, settings, provider)


def test_model_comes_from_the_provider_config(settings: Settings) -> None:
    descriptor = describe(settings, "narrator")
    assert descriptor.model_id == DEFAULT_ROLE_MODELS[Role.NARRATOR].id
    assert f"llm.invoke:{descriptor.model_id}" in descriptor.capabilities
    assert descriptor.field_sources["model_id"] is FieldSource.PROVIDER_CONFIG


def test_model_change_changes_the_definition(settings: Settings) -> None:
    nebius = describe(settings, "judge")
    local = describe(settings, "judge", "local")
    assert nebius.model_id == SUPER.id and local.model_id == settings.borges_local_model
    assert nebius.definition_sha != local.definition_sha


def test_prompt_sha_changes_when_the_prompt_text_changes(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = describe(settings, "judge")
    monkeypatch.setattr(judge, "SYSTEM", judge.SYSTEM + " Be stricter.")
    after = describe(settings, "judge")
    assert before.prompt_sha != after.prompt_sha
    assert before.definition_sha != after.definition_sha
    assert before.output_schema_sha == after.output_schema_sha


def test_component_descriptor_carries_principal_and_code_sha(settings: Settings) -> None:
    descriptor = describe(settings, "harness")
    assert "sandbox.exec" in descriptor.capabilities
    assert descriptor.principal == "agent://borges/harness"
    assert descriptor.prompt_sha is None and descriptor.code_sha is not None
    assert descriptor.model_id == "deterministic"


def test_descriptor_is_stable_and_sourced(settings: Settings) -> None:
    first, second = describe(settings, "planner"), describe(settings, "planner")
    assert first.definition_sha == second.definition_sha
    assert first.field_sources["prompt_sha"] is FieldSource.PROMPT_TEXT
    assert first.field_sources["definition_sha"] is FieldSource.COMPUTED
    assert first.output_schema_sha is not None
