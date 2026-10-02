from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from borges.api.deps import get_registry, get_settings, get_store
from borges.api.recorded_detail import recorded_origin
from borges.config import Settings
from borges.telemetry.audit_verify import ChainReport, read_records, verify_chain
from borges.telemetry.run_telemetry import AUDIT_FILE
from borges.telemetry.trace_tree import NO_SPANS_REASON, TraceResponse, build_trace

router = APIRouter()

Store = Annotated[Any, Depends(get_store)]
Config = Annotated[Settings, Depends(get_settings)]


def _known(run_id: str, store: Any, registry: Any) -> bool:
    return store.exists(run_id) or recorded_origin(registry, run_id) is not None


@router.get("/runs/{run_id}/trace")
def get_trace(
    run_id: str, store: Store, settings: Config, registry: Annotated[Any, Depends(get_registry)]
) -> TraceResponse:
    if not _known(run_id, store, registry):
        raise HTTPException(status_code=404, detail=f"Unknown run '{run_id}'.")
    if not store.exists(run_id):
        return TraceResponse(run_id=run_id, reason=NO_SPANS_REASON)
    return build_trace(run_id, settings.borges_runs_dir / run_id)


@router.get("/runs/{run_id}/audit")
def get_audit(
    run_id: str, store: Store, settings: Config, registry: Annotated[Any, Depends(get_registry)]
) -> dict[str, Any]:
    if not _known(run_id, store, registry):
        raise HTTPException(status_code=404, detail=f"Unknown run '{run_id}'.")
    if not store.exists(run_id):
        chain = ChainReport(path="", exists=False, ok=True)
        return {"run_id": run_id, "chain": chain, "records": [], "reason": NO_SPANS_REASON}
    path = settings.borges_runs_dir / run_id / AUDIT_FILE
    records = [r.model_dump(mode="json") for r in read_records(path)]
    return {"run_id": run_id, "chain": verify_chain(path), "records": records}
