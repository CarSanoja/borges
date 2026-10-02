from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from borges.api.deps import get_registry, get_settings
from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.fleet.catalog import AgentDetail, Catalog, build_catalog, build_detail
from borges.fleet.locations import open_store
from borges.fleet.templates import analysis_templates
from borges.fleet.versions import VersionRecord

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
