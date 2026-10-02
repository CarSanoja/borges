from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from borges.armor.llm_armor import LLMArmor
from borges.armor.report import ArmorReport
from borges.gateway.core import Gateway, build_gateway
from borges.gateway.dataset_columns import columns_of
from borges.llm.client import LLMClient
from borges.runs.inputs import ResolvedRun
from borges.runs.models import RunRequest
from borges.runs.orchestrator_identity import mint_identity
from borges.sandbox.backend import BranchBackend
from borges.telemetry.instrumented_backend import instrument_backend
from borges.telemetry.instrumented_llm import instrument_llm

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
