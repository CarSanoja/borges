from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from borges.api.deps import (
    get_bus,
    get_orchestrator,
    get_settings,
    get_store,
    get_uploads,
)
from borges.api.sse import sse_response
from borges.api.uploads import UploadStore
from borges.config import Settings
from borges.runs.models import (
    RunCreated,
    RunRequest,
    RunSnapshot,
    RunSummary,
    UniverseDetail,
)

if TYPE_CHECKING:
    from borges.runs.store import RunStore

router = APIRouter()
MAX_LIVE_RUNS = 2

Orchestrator = Annotated[Any, Depends(get_orchestrator)]
Store = Annotated[Any, Depends(get_store)]


def _validate_llm(request: RunRequest, settings: Settings, store: RunStore) -> None:
    llm = request.llm or settings.borges_llm
    if llm != "nebius":
        return
    if not settings.nebius_api_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "Live runs need NEBIUS_API_KEY. Set it in .env, or request "
                "llm=scripted for the offline demo."
            ),
        )
    live = [s for s in store.list_runs() if s.status == "running" and s.llm == "nebius"]
    if len(live) >= MAX_LIVE_RUNS:
        raise HTTPException(
            status_code=429,
            detail=f"At most {MAX_LIVE_RUNS} live runs can run at once. Try again soon.",
        )


def _resolve_upload(request: RunRequest, uploads: UploadStore) -> tuple[bytes, str] | None:
    if request.upload_id is None:
        return None
    if not request.question or request.decision_rule is None:
        raise HTTPException(
            status_code=400,
            detail="Uploaded datasets need both a question and a decision_rule.",
        )
    try:
        return uploads.get(request.upload_id)
    except KeyError:
        raise HTTPException(
            status_code=400, detail=f"Unknown upload '{request.upload_id}'."
        ) from None


async def _resolve(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


@router.post("/runs", status_code=202)
async def create_run(
    request: RunRequest,
    orchestrator: Orchestrator,
    store: Store,
    settings: Annotated[Settings, Depends(get_settings)],
    uploads: Annotated[UploadStore, Depends(get_uploads)],
) -> RunCreated:
    if request.case_id is None and request.upload_id is None:
        raise HTTPException(status_code=400, detail="Provide a case_id or an upload_id.")
    _validate_llm(request, settings, store)
    upload = _resolve_upload(request, uploads)
    data, name = upload if upload else (None, None)
    try:
        run_id = await _resolve(orchestrator.start(request, data=data, dataset_name=name))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown case {exc}.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RunCreated(run_id=run_id)


@router.get("/runs")
def list_runs(store: Store) -> list[RunSummary]:
    return store.list_runs()


def _require_run(store: RunStore, run_id: str) -> None:
    if not store.exists(run_id):
        raise HTTPException(status_code=404, detail=f"Unknown run '{run_id}'.")


@router.get("/runs/{run_id}")
async def get_run(run_id: str, orchestrator: Orchestrator, store: Store) -> RunSnapshot:
    _require_run(store, run_id)
    return await _resolve(orchestrator.snapshot(run_id))


@router.get("/runs/{run_id}/events")
def run_events(
    run_id: str,
    store: Store,
    bus: Annotated[Any, Depends(get_bus)],
    from_seq: Annotated[int, Query(ge=0)] = 0,
):
    _require_run(store, run_id)
    return sse_response(bus.subscribe(run_id, from_seq))


@router.get("/runs/{run_id}/universes/{universe_id}")
async def get_universe(
    run_id: str, universe_id: str, orchestrator: Orchestrator, store: Store
) -> UniverseDetail:
    _require_run(store, run_id)
    try:
        return await _resolve(orchestrator.universe_detail(run_id, universe_id))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown universe '{universe_id}'.") from None
