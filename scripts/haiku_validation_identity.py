"""Explicit, temporary model capabilities for Haiku validation only."""

from __future__ import annotations

from borges.fleet.access import capability_map
from borges.gateway.core import Gateway
from borges.gateway.policy_load import policy_for
from borges.identity.agent_tokens import AgentTokenIssuer
from borges.identity.authorizer import AgentAuthorizer, AgentGrant, tool_capability_resolver
from borges.identity.fleet_authorizer import FLEET_TOOLS, settings_audit_sink
from borges.identity.run_identity import RunIdentity
from borges.llm.client import Role


def validation_gateway(settings, run_id, model, armor, columns):
    issuer = AgentTokenIssuer()
    grants = []
    tokens = {}
    expires = 0.0
    for agent_id, (principal, capabilities) in capability_map(settings).items():
        caps = set(capabilities)
        if agent_id in {role.value for role in Role}:
            caps = {cap for cap in caps if not cap.startswith("llm.invoke:")}
            caps.add(f"llm.invoke:{model}")
        grants.append(AgentGrant(agent_id, principal, frozenset(caps)))
        tokens[agent_id] = issuer.mint(run_id, principal, caps, 3600)
        expires = issuer.verify(tokens[agent_id]).expires_at
    identity = RunIdentity(run_id=run_id, expires_at=expires, tokens=tokens)
    sink = settings_audit_sink(settings)
    resolver = tool_capability_resolver(
        FLEET_TOOLS, {"model.invoke": lambda action: f"llm.invoke:{action.target}"}
    )
    authorizer = AgentAuthorizer(grants, resolver, issuer, sink)
    gateway = Gateway(
        settings,
        run_id,
        identity,
        policy_for(settings),
        authorizer,
        sink,
        armor=armor,
        dataset_columns=columns,
    )
    return gateway, identity
