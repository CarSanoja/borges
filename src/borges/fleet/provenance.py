from __future__ import annotations

from borges.config import Settings
from borges.fleet.fleet import build_fleet
from borges.fleet.locations import open_store
from borges.fleet.models import AgentUse, RunAgents
from borges.fleet.models_in_use import Provider
from borges.gateway.policy_load import policy_for


def run_provenance(settings: Settings, provider: Provider) -> RunAgents:
    registered = build_fleet(settings)
    in_use = build_fleet(settings, provider)
    store = open_store(settings)
    uses: list[AgentUse] = []
    for descriptor in registered.agents:
        record = store.by_definition(descriptor.agent_id, descriptor.definition_sha)
        used = in_use.get(descriptor.agent_id)
        uses.append(
            AgentUse(
                agent_id=descriptor.agent_id,
                version=record.version if record else None,
                definition_sha=descriptor.definition_sha,
                approval=record.state if record else "unpublished",
                model_id=used.model_id if used else descriptor.model_id,
                prompt_sha=descriptor.prompt_sha,
                principal=descriptor.principal,
                lifecycle=descriptor.lifecycle,
                policy_sha=descriptor.policy_sha,
            )
        )
    return RunAgents(
        registry_sha=registered.registry_sha,
        agents=uses,
        policy_sha=policy_for(settings).sha,
    )
