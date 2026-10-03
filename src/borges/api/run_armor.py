from __future__ import annotations

from fastapi import HTTPException

from borges.armor.audit import record_decision
from borges.armor.audit_global import global_sink
from borges.armor.errors import ArmorRefusal
from borges.armor.request_screen import refuse_injected_request
from borges.config import Settings
from borges.identity.principal import Principal
from borges.runs.models import RunRequest


def prescreen_request(request: RunRequest, settings: Settings, principal: Principal) -> None:
    try:
        refuse_injected_request(request.question, request.decision_rule, request.column_notes)
    except ArmorRefusal as exc:
        sink = global_sink(settings, principal.id)
        for decision in exc.decisions:
            record_decision(
                decision, sink, principal.id, stage="run_request", case_id=request.case_id
            )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
