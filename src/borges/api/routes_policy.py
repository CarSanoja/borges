from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from borges.api.deps import get_settings
from borges.config import Settings
from borges.gateway.policy_view import PolicyDocument, effective_policy

router = APIRouter()

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/policy")
def get_policy(settings: SettingsDep) -> PolicyDocument:
    return effective_policy(settings)
