"""Covariates an option names as predictors but its translated spec leaves out.

"Predictors dark_skin, leagueCountry (categorical), position (categorical); use GLM" adjusts for
leagueCountry and position. A spec that keeps only the exposure fits another model under the
option's label, so the named columns are added back.

A bank_marketing_calls option at 027d581 was labelled "Logistic regression with month fixed
effects"; its spec read the covariates from ctx, so the translated spec had no month and the option
ran the baseline model, reported as a no-op. A column a label names as fixed effects or dummies is
added even when the covariates come from ctx; in the 318 recorded model labels only that option and
a job one named any.
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
EFFECTS = re.compile(
    r"\b(\w+)\s+(?:fixed[- ]effects?|dummies|dummy variables|indicators)\b"
    r"|\b(?:fixed[- ]effects?|dumm(?:y|ies)(?: variables?)?|indicators?)\s+(?:for|of|on)\s+"
    r"(?:the\s+)?(\w+)",
    re.IGNORECASE,
)


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


def with_labelled_effects(
    spec: ModelSpecOutput, label: str, available: list[str]
) -> ModelSpecOutput:
    if spec.exposure is None:
        return spec
    taken = {spec.exposure, spec.outcome, spec.offset_log, spec.moderator, *spec.covariates}
    named = [a or b for a, b in EFFECTS.findall(label)]
    missing = list(dict.fromkeys(c for c in named if c in available and c not in taken))
    if not missing:
        return spec
    return spec.model_copy(update={"covariates": [*spec.covariates, *missing]})
