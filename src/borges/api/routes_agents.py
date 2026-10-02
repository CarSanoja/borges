from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from borges.api.deps import get_registry, get_settings
from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.fleet.catalog import AgentDetail, Catalog, build_catalog, build_detail
from borges.fleet.fleet import build_fleet
from borges.fleet.governance import FourEyesViolation, change_state, publish_audited
from borges.fleet.locations import open_store
from borges.fleet.publish import Published
from borges.fleet.store import TransitionError
from borges.fleet.templates import analysis_templates
from borges.fleet.versions import VersionRecord
from borges.identity.deps import get_principal
from borges.identity.principal import Principal

router = APIRouter()

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/agents")
def list_agents(
    settings: SettingsDep,
    registry: Annotated[CaseRegistry, Depends(get_registry)],
    lifecycle: Annotated[str | None, Query()] = None,
    department: Annotated[str | None, Query()] = None,
    capability: Annotated[str | None, Query()] = None,
) -> Catalog:
    return build_catalog(settings, analysis_templates(registry), lifecycle, department, capability)


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, settings: SettingsDep) -> AgentDetail:
    detail = build_detail(settings, agent_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_id}'.")
    return detail


@router.get("/agents/{agent_id}/versions/{version}")
def get_agent_version(agent_id: str, version: str, settings: SettingsDep) -> VersionRecord:
    record = open_store(settings).get(agent_id, version)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown version '{version}' of agent '{agent_id}'."
        )
    return record


class PublishBody(BaseModel):
    message: str | None = None


class ApproveBody(BaseModel):
    reason: str | None = None


PrincipalDep = Annotated[Principal, Depends(get_principal)]


@router.post("/agents/publish")
def publish_agents(
    settings: SettingsDep, principal: PrincipalDep, body: PublishBody | None = None
) -> list[Published]:
    store = open_store(settings)
    message = body.message if body else None
    return publish_audited(store, build_fleet(settings), settings, principal.id, message)


@router.post("/agents/{agent_id}/versions/{version}/approve")
def approve_version(
    agent_id: str,
    version: str,
    settings: SettingsDep,
    principal: PrincipalDep,
    body: ApproveBody | None = None,
) -> VersionRecord:
    store = open_store(settings)
    reason = body.reason if body else None
    try:
        return change_state(store, agent_id, version, "approved", settings, principal.id, reason)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Unknown version '{version}' of agent '{agent_id}'."
        ) from None
    except FourEyesViolation as violation:
        raise HTTPException(status_code=403, detail=str(violation)) from violation
    except TransitionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
