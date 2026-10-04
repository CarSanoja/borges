"""A 0/1 exposure the option derives from a text column, such as treatment = (variant == 'B').

The template codes that indicator itself from the text column and its level, so a spec naming the
derived indicator, a column that does not exist when the step runs, is rewritten to that pair.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate_exposure import column_levels, is_text, profile_of
from borges.analysis.models import DatasetProfile

EQUALS = re.compile(r"""[`'"]?([A-Za-z_]\w*)[`'"]?\s*==\s*['"]([^'"]+)['"]""")


def _text_levels(profile: DatasetProfile | None, available: list[str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for name in available:
        column = profile_of(profile, name)
        if column is not None and is_text(column):
            found[name] = column_levels(column)
    return found


def _pairs(spec: ModelSpecOutput, text: str, levels: dict[str, list[str]]) -> set[tuple[str, str]]:
    stated = {(c, v) for c, v in EQUALS.findall(text) if v in levels.get(c, [])}
    if stated:
        return stated
    wanted = [v for v in (spec.exposure_level, spec.exposure) if v]
    return {(c, v) for c, values in levels.items() for v in wanted if v in values}


def derived_exposure(
    spec: ModelSpecOutput, text: str, available: list[str], profile: DatasetProfile | None
) -> ModelSpecOutput:
    if not spec.supported or spec.exposure is None or spec.exposure in available:
        return spec
    pairs = _pairs(spec, text, _text_levels(profile, available))
    if len(pairs) != 1:
        return spec
    column, level = next(iter(pairs))
    standardize = [n for n in spec.standardize if n != spec.exposure]
    return spec.model_copy(
        update={"exposure": column, "exposure_level": level, "standardize": standardize}
    )
