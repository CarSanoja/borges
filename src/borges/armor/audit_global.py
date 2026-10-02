from __future__ import annotations

from borges.armor.audit import AuditSink
from borges.config import Settings
from borges.telemetry.run_telemetry import global_audit_log


def global_sink(settings: Settings, principal: str | None = None) -> AuditSink:
    def emit(kind: str, **fields: object) -> None:
        decision = fields.pop("decision", None)
        reason = fields.pop("reason", None)
        actor = principal or fields.pop("principal", None)
        fields.pop("principal", None)
        global_audit_log(settings).append(
            kind, decision=decision, reason=reason, principal=actor, data=fields
        )

    return emit
