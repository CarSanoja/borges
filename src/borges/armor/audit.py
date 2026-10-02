from __future__ import annotations

from collections.abc import Callable
from typing import Any

from borges.armor.report import ARMOR_PRINCIPAL, ArmorDecision, ArmorReport
from borges.telemetry import hooks
from borges.telemetry.redaction import redact_text

AuditSink = Callable[..., None]
REASON_CHARS = 240


def run_sink(kind: str, **fields: Any) -> None:
    hooks.audit(kind, **fields)


def record_decision(
    decision: ArmorDecision,
    sink: AuditSink = run_sink,
    principal: str = ARMOR_PRINCIPAL,
    **extra: Any,
) -> None:
    reason = f"{decision.kind}: {decision.detail}"
    if decision.quote:
        reason = f"{reason} [{decision.quote}]"
    sink(
        "armor.screen",
        decision="deny" if decision.denies else "observe",
        reason=redact_text(reason, REASON_CHARS),
        principal=principal,
        action=decision.action,
        field=decision.field,
        count=decision.count,
        **extra,
    )


def record_report(
    report: ArmorReport,
    sink: AuditSink = run_sink,
    principal: str = ARMOR_PRINCIPAL,
    **extra: Any,
) -> None:
    for decision in report.decisions:
        record_decision(decision, sink, principal, **extra)
