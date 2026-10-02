from __future__ import annotations

from borges.config import Settings
from borges.fleet.fleet import Fleet
from borges.fleet.models import Approval
from borges.fleet.publish import Published, publish_fleet
from borges.fleet.store import RegistryStore
from borges.fleet.versions import VersionRecord
from borges.telemetry.audit_log import AuditLog
from borges.telemetry.run_telemetry import global_audit_log

OPERATOR = "operator"


class FourEyesViolation(PermissionError):
    pass


def _log(settings: Settings | None) -> AuditLog | None:
    return global_audit_log(settings) if settings is not None else None


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
    log = _log(settings)
    _enforce_four_eyes(store, agent_id, version, to, by, settings, log)
    record = store.transition(agent_id, version, to, by, reason)
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


def _enforce_four_eyes(
    store: RegistryStore,
    agent_id: str,
    version: str,
    to: Approval,
    by: str,
    settings: Settings | None,
    log: AuditLog | None,
) -> None:
    if to != "approved" or settings is None or not settings.borges_registry_four_eyes:
        return
    current = store.get(agent_id, version)
    if current is None or current.published_by != by:
        return
    message = f"four-eyes: {by} published {agent_id} {version} and cannot approve it"
    if log is not None:
        log.append(
            "registry.approval",
            principal=by,
            decision="deny",
            reason=message,
            data={"agent_id": agent_id, "version": version, "state": to},
        )
    raise FourEyesViolation(message)
