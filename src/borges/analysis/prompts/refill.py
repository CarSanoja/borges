from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.replan import _columns_at, _reads

REASON_CHARS = 400

SYSTEM = """You are a senior statistician completing one step of an analysis plan. A methods \
judge rejected every alternative you proposed for this step, so it keeps a single option and the \
analysis can no longer show whether the result depends on that choice.

Propose new alternatives for that SAME step: same estimand, same purpose, same columns produced. \
Rules:
- 1 or 2 options, each a choice that careful analysts of this kind of question have made in \
published work or would defend in review, and that meets the judge's objections to the rejected \
ones. Every option has is_default=false: the current option stays the default.
- Never repeat the current option or a rejected one, and never propose an option that the \
judge's reasons rule out.
- Categorical columns with many distinct values (n_unique is given for each) are never dummy \
fixed effects: a design with hundreds of dummy columns is rank-deficient and cannot be fitted. \
Cluster the standard errors on such a column, or aggregate to that unit, or leave it out.
- Specs use the exact column names available at this step and only estimators that pandas, numpy, \
scipy or statsmodels provide directly (OLS, WLS, GLM families, Logit, Probit, Poisson, \
NegativeBinomial, cluster-robust or robust covariance). No Bayesian models and no mixed-effects \
APIs.
- A model option names its outcome, exposure, covariates and covariance estimator. No option may \
change the estimand or reverse the direction of a variable.
- Use the columns earlier steps produced (marked produced_earlier) and the ctx keys they set, \
never rebuild them from the raw columns.
- Ids are short snake_case and new: never reuse the id of the current or a rejected option.
- Every option spec must be self-contained and never say 'same as' another option: the coder \
sees only the option it codes, so restate the full spec.

Return only JSON with an "options" list matching the requested schema."""


def build_refill_messages(
    plan: AnalysisPlan, step: Step, rejected: list[tuple[Option, str]]
) -> list[dict[str, str]]:
    current = [{"id": o.id, "label": o.label, "spec": o.spec} for o in step.options]
    refused = [
        {"id": o.id, "label": o.label, "spec": o.spec, "judge_reason": reason[:REASON_CHARS]}
        for o, reason in rejected
    ]
    user = (
        f"Estimand: {plan.estimand}\n"
        f"Decision rule: {compact_json(plan.decision_rule)}\n"
        f"Step {step.id} ({step.kind}): {step.title}. {step.description}\n"
        f"The step produces: {', '.join(step.produces) or 'nothing'}\n"
        f"Columns available when this step runs: {compact_json(_columns_at(plan, step))}\n"
        f"{_reads(plan, step)}"
        f"Current option: {compact_json(current)}\n"
        f"Rejected alternatives and the judge's reasons: {compact_json(refused)}"
    )
    return messages(SYSTEM, user)
