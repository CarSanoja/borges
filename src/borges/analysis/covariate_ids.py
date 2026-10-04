"""Identifier columns in a covariate list.

An identifier with many distinct values, such as a player or referee code, is no covariate: as
dummies it builds a design too wide to fit, and as a number its coding is arbitrary. The model step
can cluster the standard errors on it instead.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.ctx_covariates import covariate_names_in
from borges.analysis.model_spec.validate_exposure import is_text
from borges.analysis.models import DatasetProfile

SNAKE_ID = re.compile(r"(?:^|_)(?:id|code|num|key)$", re.IGNORECASE)
CAMEL_ID = re.compile(r"[a-z0-9](?:Id|ID|Num|Code|Short|Key)$")
ID_LEVELS = 50
TEXT_LEVELS = 200


def _id_named(name: str) -> bool:
    return SNAKE_ID.search(name) is not None or CAMEL_ID.search(name) is not None


def identifier_columns(profile: DatasetProfile | None) -> dict[str, int]:
    if profile is None:
        return {}
    return {
        c.name: c.n_unique
        for c in profile.columns
        if (c.n_unique > ID_LEVELS and _id_named(c.name))
        or (c.n_unique > TEXT_LEVELS and is_text(c))
    }


def listed_identifiers(text: str, profile: DatasetProfile | None) -> dict[str, int]:
    ids = identifier_columns(profile)
    return {name: ids[name] for name in sorted(covariate_names_in(text)) if name in ids}


def covariate_id_violations(code: str, profile: DatasetProfile | None) -> list[str]:
    return [
        f"ctx['covariates'] lists '{name}', an identifier with {levels} distinct values: it is no "
        "covariate (as dummies the design is too wide to fit, as a number its coding is "
        "arbitrary); leave it out of the list, and let the model step cluster the standard "
        "errors on it if the option asks for that"
        for name, levels in listed_identifiers(code, profile).items()
    ]
