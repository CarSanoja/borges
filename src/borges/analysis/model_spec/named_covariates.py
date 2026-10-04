"""Covariates an option names as predictors but its translated spec leaves out.

"Predictors dark_skin, leagueCountry (categorical), position (categorical); use GLM" adjusts for
leagueCountry and position. A spec that keeps only the exposure fits another model under the
option's label, so the named columns are added back.
"""

from __future__ import annotations

import re

from borges.analysis.covariate_ids import identifier_columns
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import DatasetProfile

LIST_CUE = re.compile(
    r"\b(?:predictors?|independent variables?|regressors?|covariates?|adjust(?:s|ing)? for|"
    r"control(?:s|ling)? for)\b\s*[:=]?\s*([^.;]*)",
    re.IGNORECASE,
)
STOP = re.compile(r"\b(?:use|using|with|return|fit|cluster(?:ed)?)\b", re.IGNORECASE)


def _listed(text: str, available: list[str]) -> list[str]:
    names: list[str] = []
    for segment in LIST_CUE.findall(text):
        segment = STOP.split(segment, maxsplit=1)[0]
        for column in available:
            if re.search(rf"(?<![\w]){re.escape(column)}(?![\w])", segment) and column not in names:
                names.append(column)
    return names


def with_named_covariates(
    spec: ModelSpecOutput, text: str, available: list[str], profile: DatasetProfile | None
) -> ModelSpecOutput:
    if spec.covariates_from_ctx or spec.exposure is None:
        return spec
    taken = {spec.exposure, spec.outcome, spec.offset_log, spec.moderator, spec.cluster}
    taken |= set(identifier_columns(profile))
    missing = [c for c in _listed(text, available) if c not in taken and c not in spec.covariates]
    if not missing:
        return spec
    return spec.model_copy(update={"covariates": [*spec.covariates, *missing]})
