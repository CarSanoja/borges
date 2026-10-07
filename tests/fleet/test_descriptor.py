from __future__ import annotations

import pytest

from borges.analysis.prompts import judge
from borges.config import Settings
from borges.fleet.descriptor import build_descriptor
from borges.fleet.models import FieldSource
from borges.fleet.roster import declaration_for
from borges.llm.client import DEFAULT_ROLE_MODELS, ULTRA, Role


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
    assert nebius.model_id == ULTRA.id and local.model_id == settings.borges_local_model
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


def test_policy_sha_is_part_of_the_definition(settings: Settings) -> None:
    from borges.fleet.descriptor import DEFINITION_FIELDS
    from borges.gateway.policy_view import agent_policy_sha

    judge = describe(settings, "judge")
    assert "policy_sha" in DEFINITION_FIELDS
    assert judge.policy_sha == agent_policy_sha(settings, "judge")
    assert judge.field_sources["policy_sha"] is FieldSource.POLICY_FILE
    assert describe(settings, "code_guard").policy_sha is None


def test_sandbox_components_carry_the_sandbox_policy(settings: Settings) -> None:
    from borges.gateway.policy_view import agent_policy_sha

    harness = describe(settings, "harness")
    assert harness.policy_sha == agent_policy_sha(settings, "harness", sandbox=True)


def test_fallback_models_become_capabilities(settings: Settings) -> None:
    narrator = describe(settings, "narrator")
    assert "llm.invoke:nvidia/nemotron-3-super-120b-a12b" in narrator.capabilities
    coder = describe(settings, "coder")
    assert [c for c in coder.capabilities if c.startswith("llm.invoke:")] == [
        f"llm.invoke:{coder.model_id}"
    ]


def test_a_policy_change_changes_the_definition_sha(
    settings: Settings, tmp_path, monkeypatch
) -> None:
    import json

    from borges.config import REPO_ROOT

    before = describe(settings, "judge").definition_sha
    data = json.loads((REPO_ROOT / "policy" / "gateway.json").read_text())
    data["agents"]["judge"]["max_tokens"] = 1000
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(data))
    changed = settings.model_copy(update={"borges_gateway_policy": path})
    assert describe(changed, "judge").definition_sha != before
    assert (
        describe(changed, "planner").definition_sha == describe(settings, "planner").definition_sha
    )
