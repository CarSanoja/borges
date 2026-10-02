from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from borges.config import Settings
from borges.fleet.models import RunAgents
from borges.fleet.provenance import run_provenance
from borges.llm.client import DEFAULT_ROLE_MODELS
from borges.runs.inputs import ResolvedRun
from borges.runs.ownership import owner_fields

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline


log = logging.getLogger("borges.run")


def agents_provenance(settings: Settings, llm: str) -> RunAgents | None:
    try:
        return run_provenance(settings, llm)
    except Exception:
        log.warning("agent provenance unavailable for this run", exc_info=True)
        return None


def announced_models(settings: Settings, llm: str) -> dict[str, str]:
    if llm == "local":
        return {role.value: settings.borges_local_model for role in DEFAULT_ROLE_MODELS}
    return {r.value: s.id if llm == "nebius" else llm for r, s in DEFAULT_ROLE_MODELS.items()}


def new_run_meta(
    resolved: ResolvedRun,
    llm: str,
    backend: str,
    status: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "case_id": resolved.case_id,
        "title": resolved.title,
        "status": status,
        "created_at": time.time(),
        "llm": llm,
        "backend": backend,
        "cost_usd": 0.0,
        "n_universes": 0,
        "verdict": None,
        "flipped_verdict": None,
        **owner_fields(),
        **(extra or {}),
    }


def outcome_meta(pipeline: Pipeline) -> dict[str, object]:
    report = pipeline.report
    flip = pipeline.flip
    return {
        "cost_usd": pipeline.llm.totals.cost_usd,
        "n_universes": len(pipeline.garden.universes),
        "verdict": report.original_verdict if report else None,
        "flipped_verdict": flip.flipped_verdict if flip else None,
    }
