from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from borges.api.deps import get_registry, get_settings, get_store
from borges.api.recorded_detail import recorded_dir
from borges.api.run_access import authorize_run
from borges.config import Settings
from borges.identity.deps import get_principal
from borges.identity.principal import Principal
from borges.telemetry.audit_crosscheck import verify_run_chain
from borges.telemetry.audit_verify import ChainReport, read_records
from borges.telemetry.run_telemetry import AUDIT_FILE, global_audit_path
from borges.telemetry.trace_tree import NO_SPANS_REASON, TraceResponse, build_trace

router = APIRouter()

Store = Annotated[Any, Depends(get_store)]
Config = Annotated[Settings, Depends(get_settings)]


Caller = Annotated[Principal, Depends(get_principal)]


@router.get("/runs/{run_id}/trace")
def get_trace(
    run_id: str,
    store: Store,
    settings: Config,
    registry: Annotated[Any, Depends(get_registry)],
    principal: Caller,
) -> TraceResponse:
    meta = authorize_run(store, registry, principal, run_id)
    if meta is None:
        folder = recorded_dir(registry, run_id)
        if folder is None:
            return TraceResponse(run_id=run_id, reason=NO_SPANS_REASON)
        return build_trace(run_id, folder, None)
    return build_trace(run_id, settings.borges_runs_dir / run_id, global_audit_path(settings))


@router.get("/runs/{run_id}/audit")
def get_audit(
    run_id: str,
    store: Store,
    settings: Config,
    registry: Annotated[Any, Depends(get_registry)],
    principal: Caller,
) -> dict[str, Any]:
    meta = authorize_run(store, registry, principal, run_id)
    if meta is None:
        folder = recorded_dir(registry, run_id)
        if folder is None or not (folder / AUDIT_FILE).is_file():
            chain = ChainReport(path="", exists=False, ok=True)
            return {"run_id": run_id, "chain": chain, "records": [], "reason": NO_SPANS_REASON}
        path, global_path = folder / AUDIT_FILE, None
    else:
        path, global_path = (
            settings.borges_runs_dir / run_id / AUDIT_FILE,
            global_audit_path(settings),
        )
    records = [r.model_dump(mode="json") for r in read_records(path)]
    chain = verify_run_chain(path, global_path, run_id)
    return {
        "run_id": run_id,
        "chain": chain.model_copy(update={"path": f"{run_id}/{AUDIT_FILE}"}),
        "records": records,
    }
