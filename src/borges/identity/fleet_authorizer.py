from __future__ import annotations

from borges.config import Settings
from borges.identity.actions import ToolAction
from borges.identity.agent_tokens import AgentTokenIssuer
from borges.identity.authorizer import (
    AgentAuthorizer,
    AgentGrant,
    AuditSink,
    tool_capability_resolver,
)
from borges.telemetry import hooks
from borges.telemetry.audit_record import Decision
from borges.telemetry.policy_audit import audit_global


def _model_capability(action: ToolAction) -> str:
    return f"llm.invoke:{action.target}"


FLEET_TOOLS = {
    "spend.use": "spend.use",
    "dataset.profile": "dataset.profile.read",
    "dataset.rows": "dataset.rows.read",
    "sandbox.exec": "sandbox.exec",
    "report.write": "report.write",
    "policy.enforce": "policy.enforce",
}


def settings_audit_sink(settings: Settings) -> AuditSink:
    def emit(
        kind: str,
        *,
        decision: Decision | None = None,
        reason: str | None = None,
        principal: str | None = None,
        **data: object,
    ) -> None:
        if hooks.current() is not None:
            hooks.audit(kind, decision=decision, reason=reason, principal=principal, **data)
            return
        audit_global(
            settings, kind, decision=decision, reason=reason, principal=principal, data=data
        )

    return emit


def fleet_authorizer(
    settings: Settings, issuer: AgentTokenIssuer | None = None, audit: AuditSink | None = None
) -> AgentAuthorizer:
    from borges.fleet.access import capability_map

    grants = [
        AgentGrant(agent_id, principal, caps)
        for agent_id, (principal, caps) in capability_map(settings).items()
    ]
    resolver = tool_capability_resolver(FLEET_TOOLS, {"model.invoke": _model_capability})
    return AgentAuthorizer(grants, resolver, issuer, audit or settings_audit_sink(settings))
