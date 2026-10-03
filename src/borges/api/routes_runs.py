from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse

from borges.api.awaitables import resolve
from borges.api.deps import (
    get_bus,
    get_orchestrator,
    get_registry,
    get_store,
)
from borges.api.recorded_detail import recorded_origin, recorded_snapshot
from borges.api.run_access import authorize_run, run_meta, unknown_run
from borges.api.sse import sse_response
from borges.identity.deps import get_principal
from borges.identity.principal import Principal
from borges.identity.run_access import can_read_run, can_share_run
from borges.runs.detail import build_universe_detail
from borges.runs.export_script import build_script
from borges.runs.models import RunSnapshot, RunSummary
from borges.runs.reproduce_commands import ReproducibleUniverse, script_filename, with_reproduce

if TYPE_CHECKING:
    from borges.runs.store import RunStore

router = APIRouter()

Orchestrator = Annotated[Any, Depends(get_orchestrator)]
Store = Annotated[Any, Depends(get_store)]
Caller = Annotated[Principal, Depends(get_principal)]
Registry = Annotated[Any, Depends(get_registry)]


@router.get("/runs")
def list_runs(store: Store, principal: Caller) -> list[RunSummary]:
    visible: list[RunSummary] = []
    for summary in store.list_runs():
        meta = run_meta(store, summary.run_id)
        if meta is not None and can_read_run(meta, principal):
            visible.append(summary)
    return visible


def _require_run(store: RunStore, principal: Principal, run_id: str) -> None:
    meta = run_meta(store, run_id)
    if meta is None or not can_read_run(meta, principal):
        raise unknown_run(run_id)


@router.post("/runs/{run_id}/share")
def share_run(run_id: str, store: Store, principal: Caller) -> dict[str, Any]:
    meta = run_meta(store, run_id)
    if meta is None or not can_read_run(meta, principal):
        raise unknown_run(run_id)
    if not can_share_run(meta, principal):
        raise HTTPException(status_code=403, detail="Only the run's creator can share it.")
    store.update_meta(run_id, public=True)
    return {"run_id": run_id, "public": True}


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str, orchestrator: Orchestrator, store: Store, principal: Caller
) -> RunSnapshot:
    _require_run(store, principal, run_id)
    return await resolve(orchestrator.snapshot(run_id))


@router.get("/runs/{run_id}/events")
def run_events(
    run_id: str,
    store: Store,
    principal: Caller,
    bus: Annotated[Any, Depends(get_bus)],
    from_seq: Annotated[int, Query(ge=0)] = 0,
    last_event_id: Annotated[str | None, Header()] = None,
):
    _require_run(store, principal, run_id)
    if last_event_id is not None and re.fullmatch(r"[0-9]{1,9}", last_event_id.strip()):
        from_seq = max(from_seq, int(last_event_id))
    return sse_response(bus.subscribe(run_id, from_seq))


async def _snapshot_for(
    run_id: str, orchestrator: Any, store: RunStore, registry: Any
) -> RunSnapshot:
    if store.exists(run_id):
        return await resolve(orchestrator.snapshot(run_id))
    return recorded_snapshot(registry, run_id)


@router.get("/runs/{run_id}/universes/{universe_id}")
async def get_universe(
    run_id: str,
    universe_id: str,
    orchestrator: Orchestrator,
    store: Store,
    registry: Registry,
    principal: Caller,
) -> ReproducibleUniverse:
    authorize_run(store, registry, principal, run_id)
    try:
        snapshot = await _snapshot_for(run_id, orchestrator, store, registry)
        detail = build_universe_detail(snapshot, universe_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown universe '{universe_id}'.") from None
    origin = recorded_origin(registry, run_id)
    case_id, source = origin if origin else (None, "scripted")
    return with_reproduce(detail, run_id, case_id, source)


@router.get("/runs/{run_id}/universes/{universe_id}/script")
async def get_universe_script(
    run_id: str,
    universe_id: str,
    orchestrator: Orchestrator,
    store: Store,
    registry: Registry,
    principal: Caller,
) -> PlainTextResponse:
    authorize_run(store, registry, principal, run_id)
    try:
        snapshot = await _snapshot_for(run_id, orchestrator, store, registry)
        filename = script_filename(run_id, universe_id)
        body = build_script(snapshot, universe_id, filename)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown universe '{universe_id}'.") from None
    return PlainTextResponse(
        body,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
