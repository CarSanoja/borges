from __future__ import annotations

from borges.config import Settings
from borges.fleet.fleet import Fleet
from borges.fleet.models import Approval
from borges.fleet.publish import Published, publish_fleet
from borges.fleet.store import RegistryStore
from borges.fleet.versions import VersionRecord
from borges.telemetry.audit_log import AuditLog
from borges.telemetry.run_telemetry import global_audit_path

OPERATOR = "operator"


def _log(settings: Settings | None) -> AuditLog | None:
    return AuditLog(global_audit_path(settings)) if settings is not None else None


def publish_audited(
    store: RegistryStore,
    fleet: Fleet,
    settings: Settings | None = None,
    by: str = OPERATOR,
    message: str | None = None,
) -> list[Published]:
    published = publish_fleet(store, fleet, by, message)
    log = _log(settings)
    if log is not None:
        for item in published:
            log.append(
                "registry.publish",
                principal=by,
                decision="allow",
                reason=item.changelog,
                data={
                    "agent_id": item.agent_id,
                    "version": item.version,
                    "bump": item.bump,
                    "definition_sha": item.definition_sha,
                },
            )
    return published


def change_state(
    store: RegistryStore,
    agent_id: str,
    version: str,
    to: Approval,
    settings: Settings | None = None,
    by: str = OPERATOR,
    reason: str | None = None,
) -> VersionRecord:
    record = store.transition(agent_id, version, to, by, reason)
    log = _log(settings)
    if log is not None:
        log.append(
            "registry.approval",
            principal=by,
            decision="allow",
            reason=reason,
            data={
                "agent_id": agent_id,
                "version": version,
                "state": to,
                "definition_sha": record.definition_sha,
            },
        )
    return record
