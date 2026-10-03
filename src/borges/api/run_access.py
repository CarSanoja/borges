from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from borges.api.recorded_detail import recorded_origin
from borges.identity.principal import Principal
from borges.identity.run_access import can_read_run


def unknown_run(run_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Unknown run '{run_id}'.")


def run_meta(store: Any, run_id: str) -> dict[str, Any] | None:
    try:
        if not store.exists(run_id):
            return None
        return dict(store.meta(run_id))
    except KeyError:
        return None


def authorize_run(
    store: Any, registry: Any, principal: Principal, run_id: str
) -> dict[str, Any] | None:
    meta = run_meta(store, run_id)
    if meta is not None:
        if not can_read_run(meta, principal):
            raise unknown_run(run_id)
        return meta
    if recorded_origin(registry, run_id) is None:
        raise unknown_run(run_id)
    return None
