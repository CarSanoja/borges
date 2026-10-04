"""Deterministic repairs of the spec slips the translator makes most often.

A covariate written as a formula term, C(position, drop_first=True), is the column itself: the
template dummy-encodes categorical covariates. An exposure set to the offset column is replaced by
the one exposure the option names. A derived 0/1 exposure becomes its text column and level.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.derived_exposure import derived_exposure
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate_named_exposure import named_exposures
from borges.analysis.models import DatasetProfile

TERM = re.compile(r"^\s*C\(\s*([A-Za-z_]\w*)\s*(?:,[^)]*)?\)\s*$")
FORMULA = re.compile(r"[A-Za-z_]\w*\s*~\s*([A-Za-z_]\w*)")


def _bare_covariates(spec: ModelSpecOutput, available: list[str]) -> ModelSpecOutput:
    names: list[str] = []
    for name in spec.covariates:
        match = TERM.match(name)
        bare = match.group(1) if match and match.group(1) in available else name
        if bare not in names:
            names.append(bare)
    return spec.model_copy(update={"covariates": names})


def _offset_exposure(spec: ModelSpecOutput, text: str, available: list[str]) -> ModelSpecOutput:
    if spec.exposure is None or spec.exposure != spec.offset_log:
        return spec
    named = [*named_exposures(text, available), *FORMULA.findall(text)]
    candidates = {n for n in named if n in available and n not in (spec.offset_log, spec.outcome)}
    if len(candidates) != 1:
        return spec
    exposure = next(iter(candidates))
    covariates = [c for c in spec.covariates if c != exposure]
    return spec.model_copy(update={"exposure": exposure, "covariates": covariates})


def normalise_spec(
    spec: ModelSpecOutput, text: str, available: list[str], profile: DatasetProfile | None
) -> ModelSpecOutput:
    if not spec.supported:
        return spec
    spec = _offset_exposure(_bare_covariates(spec, available), text, available)
    return derived_exposure(spec, text, available, profile)
