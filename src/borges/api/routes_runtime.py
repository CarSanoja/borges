from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from borges.api.runtime_wiring import require_runtime
from borges.identity.client_address import client_address
from borges.identity.deps import get_principal
from borges.identity.principal import Principal
from borges.runtime import audit
from borges.runtime.jobs import TERMINAL_STATES
from borges.runtime.runtime import Runtime

router = APIRouter()

Rt = Annotated[Runtime, Depends(require_runtime)]


@router.get("/runs/dead-letter")
def dead_letter(runtime: Rt) -> list[dict[str, Any]]:
    return [entry.as_dict() for entry in runtime.dead.entries()]


@router.get("/schedules")
def schedules(runtime: Rt) -> list[dict[str, Any]]:
    return [entry.as_dict() for entry in runtime.schedules.entries()]


@router.post("/runs/{run_id}/cancel", status_code=202)
async def cancel_run(
    run_id: str,
    runtime: Rt,
    principal: Annotated[Principal, Depends(get_principal)],
    http: Request,
) -> dict[str, str]:
    job = runtime.queue.get(run_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown run '{run_id}'.")
    client = client_address(http, runtime.settings)
    if not runtime.authorized(job, principal, client):
        raise HTTPException(
            status_code=403, detail="Only the run's creator or an admin can cancel it."
        )
    if job.state in TERMINAL_STATES:
        raise HTTPException(status_code=409, detail=f"The run already ended ({job.state}).")
    outcome = await runtime.cancel(run_id)
    audit.record(
        runtime.settings,
        "runtime.run.cancel",
        principal=principal.id,
        data={"run_id": run_id, "outcome": outcome},
    )
    return {"run_id": run_id, "status": outcome}
