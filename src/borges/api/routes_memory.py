from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from borges.api.deps import get_settings
from borges.config import Settings
from borges.identity.deps import get_principal
from borges.identity.principal import Principal
from borges.memory import service
from borges.memory.case_labels import with_case_labels
from borges.memory.repository import MemoryUnavailable
from borges.memory.tenant import resolve_mode, tenant_of

router = APIRouter()

FINGERPRINT = r"^[A-Za-z0-9]{8,128}$"

PrincipalDep = Annotated[Principal, Depends(get_principal)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


class NoteRequest(BaseModel):
    dataset: str = Field(pattern=FINGERPRINT)
    column: str = Field(min_length=1, max_length=service.MAX_COLUMN_CHARS)
    note: str = Field(min_length=1, max_length=service.MAX_NOTE_CHARS)


@router.get("/memory")
def memory_summary(settings: SettingsDep, principal: PrincipalDep) -> dict[str, Any]:
    return with_case_labels(service.describe(settings, principal.id), settings.borges_cases_dir)


@router.delete("/memory")
def forget_memory(
    settings: SettingsDep,
    principal: PrincipalDep,
    dataset: Annotated[str | None, Query(pattern=FINGERPRINT)] = None,
) -> dict[str, Any]:
    tenant = tenant_of(principal.id)
    removed = service.forget(settings, principal.id, tenant, dataset)
    return {"tenant": tenant, "dataset": dataset, "removed": removed}


@router.post("/memory/notes", status_code=201)
def add_note(body: NoteRequest, settings: SettingsDep, principal: PrincipalDep) -> dict[str, Any]:
    mode = resolve_mode(settings, principal.id)
    if not mode.enabled or mode.tenant is None:
        raise HTTPException(status_code=409, detail=mode.reason or "memory is not available")
    try:
        service.add_note(settings, principal.id, mode.tenant, body.dataset, body.column, body.note)
    except MemoryUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"tenant": mode.tenant, "dataset": body.dataset, "column": body.column}
