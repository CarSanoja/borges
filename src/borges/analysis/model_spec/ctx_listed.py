"""Covariates a ctx-reading spec lists as well, removed.

A marp_norms clustered-SE option at 508fe2e set covariates_from_ctx and also listed age,
gender_female and 40 country_<name> dummies, columns that do not exist when the model runs. Its
retry gave up, and the free code written instead left out the interaction's main effects. The
covariate step chooses those columns through ctx, so a name it stores there, or a dummy of a
column the step can see, is left to ctx.
"""

from __future__ import annotations

from borges.analysis.model_spec.ctx_covariates import covariate_names_in
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import AnalysisPlan, Step


def stored_names(plan: AnalysisPlan, step: Step) -> set[str]:
    names: set[str] = set()
    for earlier in plan.steps:
        if earlier.id == step.id:
            break
        for option in earlier.options:
            if option.code is not None:
                names |= covariate_names_in(option.code)
    return names


def without_ctx_listed(
    spec: ModelSpecOutput, ctx_names: list[str] | set[str], available: list[str]
) -> ModelSpecOutput:
    if not spec.covariates_from_ctx or not ctx_names:
        return spec

    def from_ctx(name: str) -> bool:
        if name in ctx_names:
            return True
        return name not in available and any(name.startswith(f"{c}_") for c in available)

    kept = [c for c in spec.covariates if not from_ctx(c)]
    return spec if kept == spec.covariates else spec.model_copy(update={"covariates": kept})
