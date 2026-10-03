from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from borges.api.awaitables import resolve
from borges.api.deps import get_orchestrator, get_settings, get_uploads
from borges.api.run_armor import prescreen_request
from borges.api.run_policy import enforce_run_policy
from borges.api.runtime_wiring import get_runtime
from borges.api.uploads import UploadStore
from borges.armor.audit import record_decision
from borges.armor.audit_global import global_sink
from borges.armor.errors import ArmorRefusal
from borges.config import Settings
from borges.identity.deps import get_principal, require_scope
from borges.identity.principal import Principal
from borges.identity.run_quota import RunQuota
from borges.identity.run_scopes import scope_for_run
from borges.runs.models import RunCreated, RunRequest
from borges.runtime.idempotency import HEADER, valid_header
from borges.runtime.runtime import Runtime
from borges.telemetry.policy_audit import audited_policy

router = APIRouter()

Orchestrator = Annotated[Any, Depends(get_orchestrator)]
REPLAY_HEADER = "Idempotent-Replay"


def _resolve_upload(request: RunRequest, uploads: UploadStore) -> tuple[bytes, str] | None:
    if request.upload_id is None:
        return None
    if not request.question or request.decision_rule is None:
        raise HTTPException(
            status_code=400,
            detail="Uploaded datasets need both a question and a decision_rule.",
        )
    try:
        return uploads.get(request.upload_id)
    except KeyError:
        raise HTTPException(
            status_code=400, detail=f"Unknown upload '{request.upload_id}'."
        ) from None


def _is_active(runtime: Runtime | None, orchestrator: Any):
    if runtime is not None:
        return runtime.is_active
    return lambda run_id: run_id in getattr(orchestrator, "tasks", {})


async def _start(
    runtime: Runtime | None,
    orchestrator: Any,
    request: RunRequest,
    principal: Principal,
    client: str,
    key: Any,
    data: bytes | None,
    name: str | None,
) -> tuple[str, bool]:
    if runtime is None:
        return await resolve(orchestrator.start(request, data=data, dataset_name=name)), True
    result = await runtime.submit(request, principal, client, key, data, name)
    return result.run_id, result.created


@router.post("/runs", status_code=202)
async def create_run(
    request: RunRequest,
    orchestrator: Orchestrator,
    settings: Annotated[Settings, Depends(get_settings)],
    uploads: Annotated[UploadStore, Depends(get_uploads)],
    principal: Annotated[Principal, Depends(get_principal)],
    runtime: Annotated[Runtime | None, Depends(get_runtime)],
    http: Request,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias=HEADER)] = None,
) -> RunCreated:
    if request.case_id is None and request.upload_id is None:
        raise HTTPException(status_code=400, detail="Provide a case_id or an upload_id.")
    if idempotency_key is not None and not valid_header(idempotency_key):
        raise HTTPException(
            status_code=400,
            detail=f"{HEADER} must be 1 to 128 characters of letters, digits and . _ : -",
        )
    require_scope(principal, scope_for_run(request, settings))
    prescreen_request(request, settings, principal)
    quota: RunQuota = http.app.state.run_quota
    client = http.client.host if http.client else "unknown"
    key = None
    if runtime is not None:
        key = runtime.idempotency(principal, client, request, idempotency_key)
        existing = runtime.lookup(key)
        if existing is not None:
            response.headers[REPLAY_HEADER] = "true"
            return RunCreated(run_id=existing)
    audited_policy(
        settings,
        "run_quota",
        quota.admit,
        principal,
        client,
        (request.llm or settings.borges_llm) == "nebius",
        _is_active(runtime, orchestrator),
        principal=principal.id,
        client=client,
    )
    request = audited_policy(
        settings,
        "run",
        enforce_run_policy,
        request,
        settings,
        orchestrator,
        principal=principal.id,
        case_id=request.case_id,
        llm=request.llm,
        upload=request.upload_id is not None,
    )
    upload = _resolve_upload(request, uploads)
    data, name = upload if upload else (None, None)
    try:
        run_id, created = await _start(
            runtime, orchestrator, request, principal, client, key, data, name
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown case {exc}.") from exc
    except ArmorRefusal as exc:
        sink = global_sink(settings, principal.id)
        for decision in exc.decisions:
            record_decision(
                decision, sink, principal.id, stage="run_request", case_id=request.case_id
            )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if created:
        quota.record(principal, client, run_id)
    else:
        response.headers[REPLAY_HEADER] = "true"
    return RunCreated(run_id=run_id)
