"""Model options a template cannot fit, written as free code without asking for a spec.

The templates fit OLS, logit, Poisson, quasi-Poisson and negative binomial models, unweighted.
Asked for anything else, the translator returned the nearest family it has: in the recordings up to
70a6102, 3 of 323 templated options named another model and ran as one of these (two
complementary log-log options in bank as logits, a Gamma GLM in marp_religiosity as OLS), and a
checkout "Weighted OLS by session length" ran without its weights.
"""

from __future__ import annotations

import re

from borges.analysis.code_guard_estimator import weighted_intent

OTHER_MODEL = re.compile(
    r"\bgamma\b|tweedie|inverse gaussian|\bprobit\b|beta regression|\btobit\b|"
    r"ordered (?:logit|probit|logistic)|ordinal (?:logit|probit|logistic|regression)|"
    r"multinomial|mixed[- ]effects?|multilevel|random (?:intercepts?|effects?|slopes?)|MixedLM|"
    r"zero[- ]inflated|hurdle|cloglog|complementary log-log|\bfirth\b|penali[sz]ed|bayesian|"
    r"quantile|\bRLM\b|M-estimat",
    re.IGNORECASE,
)
WEIGHTED_SKIP = "the option weights the observations, which a template cannot express"


def unfit_reason(intent: str) -> str | None:
    if weighted_intent(intent):
        return WEIGHTED_SKIP
    found = OTHER_MODEL.search(intent)
    if found is None:
        return None
    return f"the option names a model the templates do not fit ({found.group(0)})"
