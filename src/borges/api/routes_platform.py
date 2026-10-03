from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from borges.api import platform_core, platform_guard
from borges.api.deps import get_settings
from borges.api.platform_catalog import ORDER, PILLARS
from borges.config import Settings
from borges.identity.deps import get_principal
from borges.identity.principal import Principal

router = APIRouter()

SettingsDep = Annotated[Settings, Depends(get_settings)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]


def _guarded(read: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return read()
    except Exception as exc:
        return {"status": "error", "summary": f"{type(exc).__name__}: {exc}", "facts": {}}


@router.get("/platform")
def platform(request: Request, settings: SettingsDep, principal: PrincipalDep) -> dict[str, Any]:
    readers: dict[str, Callable[[], dict[str, Any]]] = {
        "registry": lambda: platform_core.registry(settings),
        "runtime": lambda: platform_core.runtime(request, settings),
        "memory": lambda: platform_core.memory(settings, principal),
        "identity": lambda: platform_core.identity(settings, principal),
        "gateway": lambda: platform_guard.gateway(settings),
        "armor": lambda: platform_guard.armor(settings),
        "observability": lambda: platform_guard.observability(settings),
    }
    pillars = [{"id": key, **PILLARS[key], **_guarded(readers[key])} for key in ORDER]
    return {"pillars": pillars}
