"""An outcome an earlier step builds, named by the model option but translated away.

A hurricanes plan at 027d581 had a step that wrote `outcome = np.log1p(alldeaths)` (or the square
root, or the raw count) and a model option "Regress outcome on masfem and covariates in
ctx['covariates']". The translated spec modelled alldeaths, so the transform decision had no effect
and the log-scale option reported deaths. When the option names as its regressand a column an
earlier step produces, that column is the outcome. Among 551 recorded template model codes this
was the only one whose named, produced regressand differed from the modelled outcome.

At d29a189 the option said `y = df['outcome']` instead, the template modelled alldeaths again and
the log and square-root transforms gave the same estimate. Over the recorded plans, every model spec
that assigns `y` or `endog` from a column an earlier step produces (14 of 1,315 model options)
names the outcome that step builds.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import AnalysisPlan, Step

REGRESSAND = (
    re.compile(r"\bregress(?:es|ing)?\s+(?:the\s+)?([A-Za-z_]\w*)\s+on\b", re.IGNORECASE),
    re.compile(r"\b([A-Za-z_]\w*)\s*~"),
    re.compile(r"\bdependent variable\s*(?:is|:|=)?\s*([A-Za-z_]\w*)", re.IGNORECASE),
    re.compile(r"\b(?:y|endog)\s*=\s*(?:df|data)\[\s*['\"]([A-Za-z_]\w*)['\"]\s*\]"),
)


def produced_before(plan: AnalysisPlan, step: Step) -> list[str]:
    names: list[str] = []
    for earlier in plan.steps:
        if earlier.id == step.id:
            break
        names += [n for n in earlier.produces if n not in names]
    return names


def with_produced_outcome(spec: ModelSpecOutput, text: str, produced: list[str]) -> ModelSpecOutput:
    named = [m.group(1) for pattern in REGRESSAND for m in pattern.finditer(text)]
    found = next((n for n in named if n in produced), None)
    if found is None or found == spec.outcome or found in (spec.exposure, spec.moderator):
        return spec
    standardize = [found if c == spec.outcome else c for c in spec.standardize]
    covariates = [c for c in spec.covariates if c != found]
    return spec.model_copy(
        update={"outcome": found, "standardize": standardize, "covariates": covariates}
    )
