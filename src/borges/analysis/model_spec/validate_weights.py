from __future__ import annotations

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate_exposure import is_text, profile_of
from borges.analysis.models import DatasetProfile

WEIGHTED_EXPOSURE = (
    "the model weights each row by the exposure itself, which changes the estimand and, as "
    "frequency weights, counts each row that many times: fit it unweighted, or weight by a survey "
    "or design weight the option names"
)


def weight_problems(spec: ModelSpecOutput, profile: DatasetProfile | None) -> list[str]:
    name = spec.weights
    if name is None:
        return []
    problems = []
    if name == spec.exposure:
        problems.append(WEIGHTED_EXPOSURE)
    if name == spec.outcome:
        problems.append("weights must differ from the outcome")
    if name == spec.moderator:
        problems.append(
            f"'{name}' is the moderator: a model may not weight rows by a variable it interacts"
            " with the exposure"
        )
    if is_text(profile_of(profile, name)):
        problems.append(f"weights column '{name}' is not numeric")
    if spec.cov_type == "gee":
        problems.append("weights are not available with cov_type gee")
    if spec.report == "marginal_effect":
        problems.append("marginal_effect is not available with weights")
    return problems


def mixed_problems(spec: ModelSpecOutput) -> list[str]:
    name = spec.random_intercept
    if name is None:
        return []
    problems = []
    if name in (spec.exposure, spec.outcome, spec.moderator):
        problems.append(
            f"'{name}' is a variable of the model, not a group: a random intercept for it gives "
            "every value its own intercept; use the grouping column the option names"
        )
    if spec.family != "ols":
        problems.append("a random intercept is available for the ols family only")
    if spec.cov_type != "nonrobust":
        problems.append("a random intercept is available with cov_type nonrobust only")
    if spec.offset_log is not None:
        problems.append("a random intercept is not available with an offset")
    if spec.weights is not None:
        problems.append("a random intercept is not available with weights")
    if spec.report != "coefficient":
        problems.append("a random intercept reports a coefficient only")
    return problems
