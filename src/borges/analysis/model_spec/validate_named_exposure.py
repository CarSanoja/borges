from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput

NAME = r"""[`'"]?([A-Za-z_]\w*)[`'"]?"""
CUES = (
    re.compile(
        r"\b(?:independent variables?|predictors?|exposures?|treatment variable|explanatory "
        rf"variables?|regressors?|key (?:variable|predictor))\s*(?:is|are|:|=)?\s*{NAME}",
        re.IGNORECASE,
    ),
    re.compile(rf"\bregress(?:ion)?\s+(?:of\s+)?{NAME}\s+on\s+{NAME}", re.IGNORECASE),
    re.compile(rf"\bcoefficient (?:of|for|on)\s+{NAME}", re.IGNORECASE),
)


def _named(text: str, available: list[str], cues: tuple[re.Pattern[str], ...]) -> list[str]:
    columns = set(available)
    named: list[str] = []
    for cue in cues:
        for match in cue.finditer(text):
            name = match.groups()[-1]
            if name in columns and name not in named:
                named.append(name)
    return named


def named_exposures(text: str, available: list[str]) -> list[str]:
    """Columns the option names as its exposure. An explicit mark ("x (exposure of interest)",
    coef['x']) outranks a list of independent variables, whose first item need not be it."""
    return _named(text, available, MARKED) or _named(text, available, CUES)


MARKED = (
    re.compile(rf"{NAME}\s*\([^()]*\b(?:exposure|treatment) of interest\b", re.IGNORECASE),
    re.compile(r"""\b(?:coef|coefs|params|coefficients)\[\s*['"]([A-Za-z_]\w*)['"]\s*\]"""),
    re.compile(rf"\bcoefficient (?:of|for|on)\s+{NAME}", re.IGNORECASE),
)


def named_exposure_problems(spec: ModelSpecOutput, text: str, available: list[str]) -> list[str]:
    if spec.exposure is None or spec.moderator is not None:
        return []
    named = named_exposures(text, available)
    if not named or spec.exposure in named:
        return []
    return [
        f"the option names '{named[0]}' as the exposure, but the spec reports the coefficient of "
        f"'{spec.exposure}'; set exposure to '{named[0]}' and keep '{spec.exposure}' only as a "
        "covariate if the option lists it as one"
    ]
