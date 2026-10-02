from __future__ import annotations

from typing import TYPE_CHECKING

from borges.config import Settings
from borges.llm.client import DEFAULT_ROLE_MODELS

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline


def announced_models(settings: Settings, llm: str) -> dict[str, str]:
    if llm == "local":
        return {role.value: settings.borges_local_model for role in DEFAULT_ROLE_MODELS}
    return {r.value: s.id if llm == "nebius" else llm for r, s in DEFAULT_ROLE_MODELS.items()}


def outcome_meta(pipeline: Pipeline) -> dict[str, object]:
    report = pipeline.report
    flip = pipeline.flip
    return {
        "cost_usd": pipeline.llm.totals.cost_usd,
        "n_universes": len(pipeline.garden.universes),
        "verdict": report.original_verdict if report else None,
        "flipped_verdict": flip.flipped_verdict if flip else None,
    }
