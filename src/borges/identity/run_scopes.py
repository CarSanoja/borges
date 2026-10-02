from __future__ import annotations

from borges.config import Settings
from borges.identity import scopes as s
from borges.runs.models import RunRequest


def scope_for_run(request: RunRequest, settings: Settings) -> str:
    if request.upload_id is not None:
        return s.RUNS_CREATE_LIVE_UPLOAD
    llm = request.llm or settings.borges_llm
    return s.RUNS_CREATE_LIVE_CURATED if llm in ("nebius", "local") else s.RUNS_CREATE_SCRIPTED
