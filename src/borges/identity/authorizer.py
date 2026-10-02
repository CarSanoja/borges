from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from borges.fleet.principal import agent_id_of
from borges.identity.actions import PermissionDecision, PermissionVerdict, ToolAction
from borges.identity.agent_tokens import AgentTokenInvalid, AgentTokenIssuer, process_issuer
from borges.identity.capability_ledger import (
    AuthorizationRecord,
    add_to_current_ledger,
)
from borges.identity.permission_gate import PermissionGate, Rule
from borges.telemetry import hooks

CapabilityResolver = Callable[[ToolAction], str | None]
AuditSink = Callable[..., None]

UNKNOWN_AGENT_REASON = "agent {agent_id!r} is not declared in the fleet registry"
UNMAPPED_TOOL_REASON = "tool {tool!r} maps to no declared capability; failing closed"
MISSING_CAPABILITY_REASON = (
    "agent {agent_id!r} (principal {principal_id!r}) does not hold capability "
    "{capability!r} required by {tool!r}"
)
UNKNOWN_PRINCIPAL = "unknown"
AUDIT_KIND = "identity.authorize"


@dataclass(frozen=True)
class AgentGrant:
    agent_id: str
    principal_id: str
    capabilities: frozenset[str]

    def holds(self, capability: str) -> bool:
        return capability in self.capabilities


class CapabilityDenied(PermissionError):
    def __init__(self, agent_id: str, verdict: PermissionVerdict) -> None:
        super().__init__(
            f"capability gate denied {verdict.tool} on {verdict.target!r} for "
            f"agent {agent_id}: {'; '.join(verdict.reasons)}"
        )
        self.agent_id = agent_id
        self.verdict = verdict


def tool_capability_resolver(
    mapping: dict[str, str], dynamic: dict[str, Callable[[ToolAction], str]] | None = None
) -> CapabilityResolver:
    frozen, computed = dict(mapping), dict(dynamic or {})

    def resolve(action: ToolAction) -> str | None:
        if action.tool in computed:
            return computed[action.tool](action)
        return frozen.get(action.tool)

    return resolve


class AgentAuthorizer:
    """Fail-closed capability check; every verdict reaches the ledger and the audit log."""

    def __init__(
        self,
        grants: Iterable[AgentGrant],
        resolver: CapabilityResolver,
        issuer: AgentTokenIssuer | None = None,
        audit: AuditSink | None = None,
    ) -> None:
        self._grants = {grant.agent_id: grant for grant in grants}
        self._resolver = resolver
        self._issuer = issuer or process_issuer()
        self._audit = audit or hooks.audit

    @property
    def agent_ids(self) -> list[str]:
        return sorted(self._grants)

    def grant(self, agent_id: str) -> AgentGrant | None:
        return self._grants.get(agent_id)

    def evaluate(self, agent_id: str, action: ToolAction) -> PermissionVerdict:
        return self._evaluate(self._grants.get(agent_id), agent_id, action)

    def _evaluate(
        self, grant: AgentGrant | None, agent_id: str, action: ToolAction
    ) -> PermissionVerdict:
        if grant is None:
            return self._deny(action, UNKNOWN_AGENT_REASON.format(agent_id=agent_id))
        capability = self._resolver(action)
        if capability is None:
            return self._deny(action, UNMAPPED_TOOL_REASON.format(tool=action.tool))
        if not grant.holds(capability):
            reason = MISSING_CAPABILITY_REASON.format(
                agent_id=agent_id,
                principal_id=grant.principal_id,
                capability=capability,
                tool=action.tool,
            )
            return self._deny(action, reason)
        return PermissionVerdict(
            decision=PermissionDecision.ALLOW, tool=action.tool, target=action.target
        )

    def authorize(
        self, agent_id: str, action: ToolAction, *, gate: PermissionGate | None = None
    ) -> PermissionVerdict:
        return self._decide(self._grants.get(agent_id), agent_id, action, gate)

    def authorize_token(
        self,
        token: str,
        run_id: str,
        action: ToolAction,
        *,
        gate: PermissionGate | None = None,
    ) -> PermissionVerdict:
        try:
            claims = self._issuer.verify(token, run_id=run_id)
        except AgentTokenInvalid as invalid:
            self._emit_token_denial(invalid, run_id, action)
            raise
        agent_id = agent_id_of(claims.principal) or claims.principal
        fleet_grant = self._grants.get(agent_id)
        effective = (
            AgentGrant(
                agent_id, fleet_grant.principal_id, fleet_grant.capabilities & claims.capabilities
            )
            if fleet_grant is not None and fleet_grant.principal_id == claims.principal
            else None
        )
        return self._decide(effective, agent_id, action, gate)

    def _decide(
        self,
        grant: AgentGrant | None,
        agent_id: str,
        action: ToolAction,
        gate: PermissionGate | None,
    ) -> PermissionVerdict:
        verdict = self._evaluate(grant, agent_id, action)
        if verdict.allowed and gate is not None:
            verdict = gate.evaluate(action)
        self._record(grant, agent_id, action, verdict)
        if verdict.decision != PermissionDecision.ALLOW:
            raise CapabilityDenied(agent_id, verdict)
        return verdict

    def _record(
        self,
        grant: AgentGrant | None,
        agent_id: str,
        action: ToolAction,
        verdict: PermissionVerdict,
    ) -> AuthorizationRecord:
        principal_id = grant.principal_id if grant is not None else UNKNOWN_PRINCIPAL
        record = AuthorizationRecord(
            recorded_at=datetime.now(UTC).isoformat(timespec="microseconds"),
            agent_id=agent_id,
            principal_id=principal_id,
            tool=action.tool,
            target=action.target,
            capability=self._resolver(action) or "",
            decision=verdict.decision.value,
            reasons=list(verdict.reasons),
        )
        add_to_current_ledger(record)
        self._emit(record)
        return record

    def _emit(self, record: AuthorizationRecord) -> None:
        allowed = record.decision == PermissionDecision.ALLOW.value
        self._audit(
            AUDIT_KIND,
            decision="allow" if allowed else "deny",
            reason=None if allowed else "; ".join(record.reasons),
            principal=record.principal_id,
            agent_id=record.agent_id,
            tool=record.tool,
            target=record.target,
            capability=record.capability,
            verdict=record.decision,
        )

    def _emit_token_denial(
        self, invalid: AgentTokenInvalid, run_id: str, action: ToolAction
    ) -> None:
        self._audit(
            AUDIT_KIND,
            decision="deny",
            reason=str(invalid),
            principal=UNKNOWN_PRINCIPAL,
            run=run_id,
            tool=action.tool,
            target=action.target,
            failure=invalid.failure,
        )

    def capability_rule(self, agent_id: str) -> Rule:
        def rule(action: ToolAction) -> PermissionDecision | None:
            verdict = self.evaluate(agent_id, action)
            return None if verdict.allowed else verdict.decision

        return rule

    @staticmethod
    def _deny(action: ToolAction, reason: str) -> PermissionVerdict:
        return PermissionVerdict(
            decision=PermissionDecision.DENY,
            tool=action.tool,
            target=action.target,
            reasons=[reason],
        )
