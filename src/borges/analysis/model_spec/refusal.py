"""A refusal of an option the templates express, asked once more.

In the teaching_ratings run of 6 Oct (tr3) the spec model refused "Fit statsmodels MixedLM ...
random intercept for 'prof'" as outside the supported families, although random_intercept
expresses it; the free code written instead returned a non-finite estimate. The option had
already passed unfit_reason, the deterministic check for what no template can express, so a
refusal there is more often a misreading than a limit, and one more question is cheap.
"""

from __future__ import annotations

from borges.analysis.model_spec.schema import ModelSpecOutput

RECONSIDER = (
    "You returned supported false ({reason}). This option passed the check for what the "
    "templates cannot express, and the spec has fields for: a linear mixed model with one random "
    'intercept (family "ols", random_intercept set to the grouping column), weighted least '
    "squares or a weighted GLM (weights set to the weight column), robust or clustered standard "
    "errors (cov_type, cluster), an interaction (moderator), an offset (offset_log) and "
    "covariates. Translate the option with these fields. Return supported false again only "
    "when none of them expresses it, with the reason."
)


def reconsider(refused: ModelSpecOutput) -> list[dict[str, str]]:
    reason = refused.reason or "no reason given"
    return [
        {"role": "assistant", "content": refused.model_dump_json()},
        {"role": "user", "content": RECONSIDER.format(reason=reason)},
    ]
