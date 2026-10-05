"""A 0/1 exposure the option cuts from a numeric column, such as dark = (skin_tone >= 0.5).

A red-cards spec turned that cut into exposure_level '0.5', and the template coded 1 for a skin
tone of exactly 0.5; the free-code option of the same step coded a missing skin tone as light
(b4e2f4e). The template now cuts the column itself, after dropping the rows where it is missing,
and a spec whose option states one cut on an available column that is not text, while the spec
names that column or a derived name that does not exist, is rewritten to the column and the cut.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate_exposure import is_text, profile_of
from borges.analysis.models import DatasetProfile

CUT = re.compile(r"""[`'"]?([A-Za-z_]\w*)[`'"]?\s*(?:\]\s*)?>=\s*(-?\d+(?:\.\d+)?)""")


def stated_cuts(
    text: str, available: list[str], profile: DatasetProfile | None
) -> set[tuple[str, float]]:
    return {
        (column, float(value))
        for column, value in CUT.findall(text)
        if column in available and not is_text(profile_of(profile, column))
    }


def threshold_exposure(
    spec: ModelSpecOutput, text: str, available: list[str], profile: DatasetProfile | None
) -> ModelSpecOutput:
    if not spec.supported or spec.exposure is None or spec.exposure_threshold is not None:
        return spec
    cuts = stated_cuts(text, available, profile)
    if len(cuts) != 1:
        return spec
    column, cut = next(iter(cuts))
    if spec.exposure != column and spec.exposure in available:
        return spec
    standardize = [n for n in spec.standardize if n not in (spec.exposure, column)]
    update = {
        "exposure": column,
        "exposure_threshold": cut,
        "exposure_level": None,
        "standardize": standardize,
    }
    return spec.model_copy(update=update)
