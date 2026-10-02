from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from borges.armor.llm_armor import LLMArmor
from borges.armor.report import ArmorReport
from borges.fleet.models import RunAgents
from borges.gateway.core import Gateway, build_gateway
from borges.gateway.dataset_columns import columns_of
from borges.llm.client import LLMClient
from borges.memory.factory import build_run_memory
from borges.memory.run_memory import RunMemory
from borges.runs.inputs import ResolvedRun
from borges.runs.models import RunRequest
from borges.runs.orchestrator_identity import mint_identity
from borges.sandbox.backend import BranchBackend
from borges.telemetry.instrumented_backend import instrument_backend
from borges.telemetry.instrumented_llm import instrument_llm

log = logging.getLogger("borges.run")

if TYPE_CHECKING:
    from borges.runs.orchestrator import RunOrchestrator


def build_gateway_and_llm(
    orchestrator: RunOrchestrator,
    run_id: str,
    request: RunRequest,
    resolved: ResolvedRun,
    armor_report: ArmorReport,
) -> tuple[Gateway, LLMClient]:
    options: dict[str, Path | None] = {"fixtures_dir": resolved.fixtures_dir}
    if orchestrator.record_dir is not None:
        options["record_dir"] = orchestrator.record_dir
    settings = orchestrator.settings
    identity = mint_identity(settings, run_id)
    gateway = build_gateway(
        settings,
        run_id,
        identity,
        orchestrator.modes(request)[0],
        armor=LLMArmor(armor_report),
        dataset_columns=columns_of(resolved.data),
    )
    raw = orchestrator.llm_factory(settings, request.llm, **options)
    return gateway, instrument_llm(raw, identity, gateway)


def build_backend(
    orchestrator: RunOrchestrator, request: RunRequest, gateway: Gateway
) -> BranchBackend:
    return instrument_backend(
        orchestrator.backend_factory(orchestrator.settings, request.backend), gateway
    )


def build_memory(
    orchestrator: RunOrchestrator,
    run_id: str,
    request: RunRequest,
    resolved: ResolvedRun,
    agents: RunAgents | None,
    armor_report: ArmorReport,
    resumed: bool,
) -> RunMemory | None:
    if not orchestrator.settings.borges_memory:
        return None
    principal = orchestrator.store.meta(run_id).get("principal")
    curated_as_is = (
        resolved.case_id is not None
        and request.upload_id is None
        and request.question is None
        and request.decision_rule is None
        and not request.column_notes
    )
    try:
        return build_run_memory(
            orchestrator.settings,
            principal if isinstance(principal, str) else None,
            run_id,
            agents,
            armor_report,
            curated_as_is,
            reads=not resumed,
        )
    except Exception:
        log.warning("memory unavailable for this run", exc_info=True)
        return None
