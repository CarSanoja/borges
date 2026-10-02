from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from borges.api.deps import get_settings, get_uploads
from borges.api.run_policy import enforce_upload_policy
from borges.api.uploads import MAX_BYTES, UploadQuotaError, UploadStore
from borges.armor.audit import record_decision
from borges.armor.audit_global import global_sink
from borges.armor.errors import ArmorRefusal
from borges.config import Settings
from borges.identity.deps import get_principal
from borges.identity.principal import Principal
from borges.telemetry.policy_audit import audited_policy

router = APIRouter()


@router.post("/uploads")
async def create_upload(
    file: Annotated[UploadFile, File()],
    uploads: Annotated[UploadStore, Depends(get_uploads)],
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[Principal, Depends(get_principal)],
) -> dict[str, Any]:
    audited_policy(settings, "upload", enforce_upload_policy, settings, principal=principal.id)
    content = await file.read(MAX_BYTES + 1)
    try:
        upload_id, profile = await asyncio.to_thread(
            uploads.put, content, file.filename or "upload.csv"
        )
    except UploadQuotaError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ArmorRefusal as exc:
        sink = global_sink(settings, principal.id)
        for decision in exc.decisions:
            record_decision(decision, sink, principal.id, stage="upload")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    pii = uploads.pii(upload_id)
    if pii.total_detections:
        global_sink(settings, principal.id)(
            "armor.upload_scan",
            decision="observe",
            reason=f"personal data found in {len(pii.columns)} column(s)",
            upload_id=upload_id,
            columns={c.column: c.kinds for c in pii.columns},
        )
    return {
        "upload_id": upload_id,
        "profile": profile.model_dump(mode="json"),
        "pii": pii.model_dump(mode="json"),
    }
