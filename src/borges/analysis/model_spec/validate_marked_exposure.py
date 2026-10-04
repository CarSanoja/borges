"""The exposure the dataset notes mark as the one of interest.

A bank model option asked for the coefficient of campaign_w, a column the default of the earlier
step does not build. The spec request then reported the coefficient of `contact` ("contact call"
read as a column) while the clustered option of the same step reported `campaign`, so the original
verdict came from another exposure: an odds ratio of 1.30 against 0.89, and a flip that was only
a change of exposure (2a2d925). When the notes mark one column as the exposure of interest, a spec
that reports the coefficient of another column of the dataset is refused. A column an earlier step
builds is allowed: it may be the marked column transformed.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import DatasetProfile

MARK = re.compile(r"\bexposure of interest\b", re.IGNORECASE)


def marked_exposure(profile: DatasetProfile | None) -> str | None:
    if profile is None:
        return None
    marked = [c.name for c in profile.columns if c.note and MARK.search(c.note)]
    return marked[0] if len(marked) == 1 else None


def marked_exposure_problems(spec: ModelSpecOutput, profile: DatasetProfile | None) -> list[str]:
    marked = marked_exposure(profile)
    if marked is None or profile is None or spec.exposure is None or spec.moderator is not None:
        return []
    raw = {c.name for c in profile.columns}
    if spec.exposure == marked or spec.exposure not in raw:
        return []
    return [
        f"the dataset notes mark '{marked}' as the exposure of interest, but the spec reports the "
        f"coefficient of '{spec.exposure}'; set exposure to '{marked}' and keep "
        f"'{spec.exposure}' only as a covariate if the option lists it as one"
    ]
