from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from borges.config import Settings
from borges.fleet.enforcement import Blocker, unapproved
from borges.fleet.fleet import Fleet, build_fleet
from borges.fleet.locations import open_store
from borges.fleet.models import AgentDescriptor
from borges.fleet.store import RegistryStore
from borges.fleet.versions import VersionRecord
from borges.gateway.policy_load import policy_for
from borges.gateway.policy_models import SandboxPolicy
from borges.gateway.policy_view import AgentPolicyView, agent_view


class AgentCard(BaseModel):
    agent_id: str
    display_name: str
    purpose: str
    kind: str
    role: str
    model_id: str
    lifecycle: str
    department: str
    owner: str
    principal: str
    capabilities: list[str]
    prompt_sha: str | None
    output_schema_sha: str | None
    code_sha: str | None
    policy_sha: str | None
    policy: AgentPolicyView | None
    sandbox_policy: SandboxPolicy | None
    definition_sha: str
    version: str | None
    approval: str
    latest_version: str | None
    versions: int


class AnalysisTemplate(BaseModel):
    id: str
    title: str
    owner: str
    question: str
    metric: str
    decision_rule: dict[str, Any]
    dataset_name: str
    live_only: bool


class CatalogSummary(BaseModel):
    total: int
    by_lifecycle: dict[str, int]
    by_approval: dict[str, int]
    enforce: bool
    blocked: list[Blocker]


class Catalog(BaseModel):
    registry_sha: str
    summary: CatalogSummary
    agents: list[AgentCard]
    templates: list[AnalysisTemplate]


class AgentDetail(BaseModel):
    descriptor: AgentDescriptor
    card: AgentCard
    versions: list[VersionRecord]


def card_for(descriptor: AgentDescriptor, store: RegistryStore, settings: Settings) -> AgentCard:
    versions = store.versions_of(descriptor.agent_id)
    current = store.by_definition(descriptor.agent_id, descriptor.definition_sha)
    fields = descriptor.model_dump(exclude={"field_sources"})
    loaded = policy_for(settings)
    agent = loaded.agent(descriptor.agent_id)
    return AgentCard(
        **fields,
        policy=agent_view(agent) if agent else None,
        sandbox_policy=loaded.policy.sandbox if "sandbox.exec" in descriptor.capabilities else None,
        version=current.version if current else None,
        approval=current.state if current else "unpublished",
        latest_version=versions[-1].version if versions else None,
        versions=len(versions),
    )


def _matches_capability(card: AgentCard, wanted: str) -> bool:
    return any(item == wanted or item.split(":")[0] == wanted for item in card.capabilities)


def filter_cards(
    cards: list[AgentCard],
    lifecycle: str | None = None,
    department: str | None = None,
    capability: str | None = None,
) -> list[AgentCard]:
    return [
        card
        for card in cards
        if (lifecycle is None or card.lifecycle == lifecycle)
        and (department is None or card.department == department)
        and (capability is None or _matches_capability(card, capability))
    ]


def _count(values: list[str]) -> dict[str, int]:
    return {value: values.count(value) for value in sorted(set(values))}


def build_catalog(
    settings: Settings,
    templates: list[AnalysisTemplate],
    lifecycle: str | None = None,
    department: str | None = None,
    capability: str | None = None,
) -> Catalog:
    fleet = build_fleet(settings)
    store = open_store(settings)
    every = [card_for(item, store, settings) for item in fleet.agents]
    summary = CatalogSummary(
        total=len(every),
        by_lifecycle=_count([c.lifecycle for c in every]),
        by_approval=_count([c.approval for c in every]),
        enforce=settings.borges_registry_enforce,
        blocked=unapproved(fleet, store),
    )
    shown = filter_cards(every, lifecycle, department, capability)
    return Catalog(
        registry_sha=fleet.registry_sha, summary=summary, agents=shown, templates=templates
    )


def build_detail(settings: Settings, agent_id: str) -> AgentDetail | None:
    fleet: Fleet = build_fleet(settings)
    descriptor = fleet.get(agent_id)
    if descriptor is None:
        return None
    store = open_store(settings)
    return AgentDetail(
        descriptor=descriptor,
        card=card_for(descriptor, store, settings),
        versions=store.versions_of(agent_id),
    )
