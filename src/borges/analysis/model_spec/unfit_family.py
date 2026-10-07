"""Model options a template cannot fit, written as free code without asking for a spec.

The templates fit OLS, logit, Poisson, quasi-Poisson and negative binomial models, with weights
from a column, and a linear random-intercept model with one grouping column.
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
COMPUTED_WEIGHTS = re.compile(
    r"inverse[- ](?:probability|variance|propensity)|\bIPW\b|propensity|1\s*/|\braking\b|"
    r"post-?stratif|entropy balanc|survey design|svyglm|calibrat",
    re.IGNORECASE,
)
RANDOM_INTERCEPT = re.compile(
    r"random[- ]intercepts?(?: only)?|MixedLM|(?:linear )?mixed[- ](?:effects?[- ])?"
    r"(?:linear )?(?:models?|regression)|multilevel (?:linear )?(?:models?|regression)|"
    r"hierarchical linear model",
    re.IGNORECASE,
)
MIXED_BEYOND = re.compile(
    r"slopes?|crossed|nested|GLMM|generalized linear mixed|random coefficients?|"
    r"(?:logit|logistic|poisson|binomial|probit|gamma|count)\b.*\bmixed|"
    r"mixed\b.*\b(?:logit|logistic|poisson|binomial|probit|gamma|count)\b",
    re.IGNORECASE,
)


def _named(found: re.Match[str]) -> str:
    return f"the option names a model the templates do not fit ({found.group(0)})"


def unfit_reason(intent: str) -> str | None:
    weighted = weighted_intent(intent)
    if weighted and COMPUTED_WEIGHTS.search(intent):
        return WEIGHTED_SKIP
    intercept = RANDOM_INTERCEPT.search(intent)
    rest = RANDOM_INTERCEPT.sub(" ", intent)
    if intercept is not None:
        beyond = MIXED_BEYOND.search(intent)
        if beyond is not None:
            return _named(beyond)
        if weighted:
            return WEIGHTED_SKIP
    found = OTHER_MODEL.search(rest)
    return None if found is None else _named(found)
