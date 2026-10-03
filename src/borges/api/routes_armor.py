from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from borges.api.deps import get_settings
from borges.armor.injection import MODEL_OUTPUT, UNTRUSTED_INPUT, screen_text
from borges.armor.pii import count_pii, redact_pii
from borges.armor.report import QUARANTINE_TOKEN
from borges.config import Settings
from borges.identity.deps import get_principal
from borges.identity.principal import Principal
from borges.identity.rate_limit import RateLimiter

router = APIRouter()

MAX_TEXT_CHARS = 4000
CHECK_BURST = 20
CHECK_PER_S = 0.5

Field_ = Literal["question", "column_note", "model_output"]


class ArmorCheckBody(BaseModel):
    text: str = Field(max_length=MAX_TEXT_CHARS)
    field: Field_ = "question"


def check_limiter(request: Request) -> RateLimiter:
    state: Any = request.app.state
    limiter = getattr(state, "armor_limiter", None)
    if limiter is None:
        settings: Settings = state.settings
        tight = settings.model_copy(
            update={
                "borges_rate_anon_burst": CHECK_BURST,
                "borges_rate_anon_per_s": CHECK_PER_S,
                "borges_rate_key_burst": CHECK_BURST * 4,
                "borges_rate_key_per_s": CHECK_PER_S * 4,
            }
        )
        limiter = RateLimiter(tight)
        state.armor_limiter = limiter
    return limiter


def _action(field: Field_, flagged: bool) -> str:
    if not flagged:
        return "pass"
    return "refuse" if field == "question" else "quarantine"


@router.post("/armor/check")
def armor_check(
    body: ArmorCheckBody,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    client = request.client.host if request.client else "unknown"
    state = check_limiter(request).take(principal, client)
    if not state.allowed:
        retry = max(1, int(state.retry_after_s + 0.999))
        raise HTTPException(
            status_code=429,
            detail=f"Armor dry-run rate limit exceeded; retry in {retry}s.",
            headers={"Retry-After": str(retry)},
        )
    profile = MODEL_OUTPUT if body.field == "model_output" else UNTRUSTED_INPUT
    findings = screen_text(body.text, profile)
    pii = dict(count_pii(body.text))
    action = _action(body.field, bool(findings))
    shown = QUARANTINE_TOKEN if action == "quarantine" else redact_pii(body.text)
    return {
        "action": action,
        "flagged": bool(findings),
        "field": body.field,
        "screen": profile.name,
        "findings": [
            {"category": f.category, "technique": f.technique, "quote": f.quote} for f in findings
        ],
        "pii": pii,
        "text_after_armor": None if action == "refuse" else shown,
        "stored": False,
        "second_stage_llm": settings.borges_armor_llm,
    }
