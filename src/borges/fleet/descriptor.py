from __future__ import annotations

from borges.config import Settings
from borges.fleet.declarations import AgentDeclaration
from borges.fleet.fingerprints import code_sha, prompt_sha, schema_sha
from borges.fleet.models import AgentDescriptor, FieldSource
from borges.fleet.models_in_use import DETERMINISTIC_MODEL, Provider, model_for
from borges.fleet.principal import agent_principal
from borges.fleet.prompt_texts import system_prompt
from borges.telemetry.hashing import sha256_json

DEFINITION_FIELDS = (
    "agent_id",
    "display_name",
    "purpose",
    "kind",
    "role",
    "model_id",
    "prompt_sha",
    "output_schema_sha",
    "code_sha",
    "capabilities",
    "principal",
    "lifecycle",
    "owner",
    "department",
)


def _capabilities(declaration: AgentDeclaration, model_id: str) -> list[str]:
    declared = list(declaration.capabilities)
    if declaration.llm_role is not None:
        declared.append(f"llm.invoke:{model_id}")
    return sorted(set(declared))


def _sources(declaration: AgentDeclaration) -> dict[str, FieldSource]:
    sources = {name: FieldSource.DECLARED for name in DEFINITION_FIELDS}
    sources["principal"] = FieldSource.COMPUTED
    sources["model_id"] = (
        FieldSource.PROVIDER_CONFIG if declaration.llm_role else FieldSource.DECLARED
    )
    sources["prompt_sha"] = (
        FieldSource.PROMPT_TEXT if declaration.llm_role else FieldSource.DECLARED
    )
    sources["output_schema_sha"] = (
        FieldSource.OUTPUT_SCHEMA if declaration.output_schema else FieldSource.DECLARED
    )
    sources["code_sha"] = (
        FieldSource.SOURCE_CODE if declaration.code_files else FieldSource.DECLARED
    )
    sources["capabilities"] = (
        FieldSource.PROVIDER_CONFIG if declaration.llm_role else FieldSource.DECLARED
    )
    sources["definition_sha"] = FieldSource.COMPUTED
    return sources


def definition_sha_of(fields: dict[str, object]) -> str:
    return sha256_json({name: fields[name] for name in DEFINITION_FIELDS})


def build_descriptor(
    declaration: AgentDeclaration, settings: Settings, provider: Provider = "nebius"
) -> AgentDescriptor:
    model_id = (
        model_for(declaration.llm_role, settings, provider)
        if declaration.llm_role
        else DETERMINISTIC_MODEL
    )
    fields: dict[str, object] = {
        "agent_id": declaration.agent_id,
        "display_name": declaration.display_name,
        "purpose": declaration.purpose,
        "kind": declaration.kind,
        "role": declaration.role,
        "model_id": model_id,
        "prompt_sha": prompt_sha(system_prompt(declaration.agent_id)),
        "output_schema_sha": schema_sha(declaration.output_schema),
        "code_sha": code_sha(declaration.code_files),
        "capabilities": _capabilities(declaration, model_id),
        "principal": agent_principal(declaration.agent_id),
        "lifecycle": declaration.lifecycle,
        "owner": declaration.owner,
        "department": declaration.department,
    }
    return AgentDescriptor.model_validate(
        {
            **fields,
            "definition_sha": definition_sha_of(fields),
            "field_sources": _sources(declaration),
        }
    )
