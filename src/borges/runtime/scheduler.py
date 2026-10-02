from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import HTTPException

from borges.api.run_policy import enforce_run_policy
from borges.identity.principal import Principal
from borges.identity.scopes import PUBLIC_SCOPES
from borges.runs.models import RunRequest
from borges.runtime import audit
from borges.runtime.idempotency import schedule_key
from borges.runtime.schedules import Schedule

if TYPE_CHECKING:
    from borges.runtime.runtime import Runtime

log = logging.getLogger("borges.runtime")
SCHEDULER_CLIENT = "scheduler"


def schedule_principal(schedule: Schedule) -> Principal:
    return Principal(id=schedule.principal, kind="key", scopes=PUBLIC_SCOPES)


async def submit_due(runtime: Runtime, schedule: Schedule) -> str | None:
    request = RunRequest(case_id=schedule.case_id, llm=schedule.llm)  # type: ignore[arg-type]
    try:
        request = enforce_run_policy(request, runtime.settings, runtime.orchestrator)
        result = await runtime.submit(
            request,
            schedule_principal(schedule),
            SCHEDULER_CLIENT,
            key=schedule_key(schedule.id, schedule.next_run),
            source="schedule",
            schedule_id=schedule.id,
        )
    except HTTPException as skipped:
        log.info("schedule %s skipped: %s", schedule.id, skipped.detail)
        return None
    except (KeyError, ValueError) as invalid:
        log.warning("schedule %s cannot run: %s", schedule.id, invalid)
        runtime.schedules.advance(schedule, None)
        return None
    audit.record(
        runtime.settings,
        "runtime.schedule.submitted",
        principal=schedule.principal,
        data={"schedule_id": schedule.id, "run_id": result.run_id, "case_id": schedule.case_id},
    )
    return result.run_id


async def run_due(runtime: Runtime) -> list[str]:
    submitted: list[str] = []
    for schedule in runtime.schedules.due():
        run_id = await submit_due(runtime, schedule)
        if run_id is not None:
            submitted.append(run_id)
            runtime.schedules.advance(schedule, run_id)
    return submitted
