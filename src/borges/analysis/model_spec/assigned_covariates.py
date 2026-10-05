"""Covariates a model option assigns to ctx itself.

A checkout adversary option at 5fb4084, "OLS with winsorized session length covariate", was the
spec of a covariate step placed in the model step: "Set ctx['covariates'] =
['winsorized_session_seconds']; where winsorized_session_seconds is computed as session_seconds
winsorized at the 5th and 95th percentiles". The template read the earlier step's covariates and
fitted the baseline model under that label. Among 269 recorded model specs it is the only one that
assigns ctx['covariates']. The assigned columns are the model's covariates; when one of them does
not exist yet the template cannot build it, and the option is written as free code before the
template is asked for.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.interaction import own_text
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import Option

ASSIGNED = re.compile(r"ctx\[\s*['\"]covariates['\"]\s*\]\s*=\s*\[([^\]]*)\]")
NAME = re.compile(r"['\"]([^'\"]+)['\"]")
UNBUILT = (
    "the option assigns covariates the data does not have yet, which a template cannot build; "
    "written as free code: "
)


def assigned_covariates(option: Option) -> list[str] | None:
    found = ASSIGNED.search(own_text(option))
    return None if found is None else NAME.findall(found.group(1))


def unbuilt_covariates(option: Option, available: list[str]) -> list[str]:
    return [c for c in assigned_covariates(option) or [] if c not in available]


def with_assigned_covariates(
    spec: ModelSpecOutput, option: Option, available: list[str]
) -> ModelSpecOutput:
    names = assigned_covariates(option)
    if names is None or any(c not in available for c in names):
        return spec
    taken = {spec.exposure, spec.outcome, spec.moderator}
    covariates = [c for c in names if c not in taken]
    return spec.model_copy(update={"covariates": covariates, "covariates_from_ctx": False})
