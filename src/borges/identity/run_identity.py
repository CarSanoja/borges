from __future__ import annotations

from dataclasses import dataclass, field

from borges.config import Settings
from borges.fleet.access import capability_map
from borges.identity.agent_tokens import AgentTokenIssuer, process_issuer
from borges.telemetry import hooks

ORCHESTRATOR_PRINCIPAL = "system://borges/orchestrator"
MINT_KIND = "identity.agent_tokens.minted"


@dataclass(frozen=True)
class RunIdentity:
    run_id: str
    expires_at: float
    tokens: dict[str, str] = field(default_factory=dict, repr=False)

    def token_for(self, agent_id: str) -> str | None:
        return self.tokens.get(agent_id)


def mint_run_identity(
    settings: Settings, run_id: str, issuer: AgentTokenIssuer | None = None
) -> RunIdentity:
    chosen = issuer or process_issuer()
    ttl = float(settings.borges_agent_token_ttl_s)
    tokens: dict[str, str] = {}
    expires = 0.0
    for agent_id, (principal, capabilities) in capability_map(settings).items():
        token = chosen.mint(run_id, principal, capabilities, ttl)
        tokens[agent_id] = token
        expires = chosen.verify(token).expires_at
    identity = RunIdentity(run_id=run_id, expires_at=expires, tokens=tokens)
    hooks.audit(
        MINT_KIND,
        decision="allow",
        principal=ORCHESTRATOR_PRINCIPAL,
        agents=sorted(tokens),
        expires_at=expires,
        ttl_s=ttl,
    )
    return identity
