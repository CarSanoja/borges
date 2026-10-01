from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from borges.api.deps import get_uploads
from borges.api.uploads import MAX_BYTES, UploadStore

router = APIRouter()


@router.post("/uploads")
async def create_upload(
    file: Annotated[UploadFile, File()],
    uploads: Annotated[UploadStore, Depends(get_uploads)],
) -> dict[str, Any]:
    content = await file.read(MAX_BYTES + 1)
    try:
        upload_id, profile = uploads.put(content, file.filename or "upload.csv")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"upload_id": upload_id, "profile": profile.model_dump(mode="json")}
