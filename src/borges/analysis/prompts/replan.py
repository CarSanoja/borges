from __future__ import annotations

from borges.analysis.models import AnalysisPlan, ColumnProfile, Step
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.coder import _available_columns

TEXT_DTYPES = ("object", "str", "string", "category")
ERROR_CHARS = 600

SYSTEM = """You are a senior statistician repairing one step of an analysis plan. Every option \
you proposed for the step failed to run on the data, so the step has no working option and the \
whole analysis would stop.

Propose replacement options for that SAME step: same estimand, same purpose, same columns \
produced. Rules:
- 1 to 4 options, each a real alternative a careful analyst could defend, exactly one with \
is_default=true (the most conventional one that can actually run).
- Read the errors of the failed options and design around their cause. Do not repeat a failed \
option, and do not propose anything that fails for the same reason.
- Categorical columns with many distinct values (n_unique is given for each) are never dummy \
fixed effects: a design with hundreds of dummy columns is rank-deficient and cannot be fitted. \
Cluster the standard errors on such a column, or aggregate to that unit, or leave it out.
- Specs use the exact column names available at this step and only estimators that pandas, numpy, \
scipy or statsmodels provide directly (OLS, WLS, GLM families, Logit, Probit, Poisson, \
NegativeBinomial, cluster-robust or robust covariance). No Bayesian models and no mixed-effects \
APIs unless the failed errors show them working.
- A model option names its outcome, exposure, covariates and covariance estimator. No option may \
change the estimand or reverse the direction of a variable.
- Use the columns earlier steps produced (marked produced_earlier) and the ctx keys they set, \
never rebuild them from the raw columns: the alternatives of an earlier step only matter if this \
step reads what they produce.
- Ids are short snake_case and new: never reuse the id of a failed option.
- Every option spec must be self-contained and never say 'same as' another option: the coder \
sees only the option it codes, so restate the full spec.

Return only JSON with an "options" list matching the requested schema."""


def _column(column: ColumnProfile) -> dict[str, object]:
    entry: dict[str, object] = {"name": column.name, "dtype": column.dtype}
    if column.dtype.startswith(TEXT_DTYPES):
        entry["n_unique"] = column.n_unique
    return entry


def _columns_at(plan: AnalysisPlan, step: Step) -> list[dict[str, object]]:
    profiled = {c.name: c for c in plan.dataset.columns}
    return [
        _column(profiled[name]) if name in profiled else {"name": name, "produced_earlier": True}
        for name in _available_columns(plan, step)
    ]


def build_replan_messages(
    plan: AnalysisPlan, step: Step, failures: list[tuple[str, str, str, str]]
) -> list[dict[str, str]]:
    failed = [
        {"id": oid, "label": label, "spec": spec, "error": (error or "unknown")[:ERROR_CHARS]}
        for oid, label, spec, error in failures
    ]
    produces = ", ".join(step.produces) or "nothing"
    user = (
        f"Estimand: {plan.estimand}\n"
        f"Decision rule: {compact_json(plan.decision_rule)}\n"
        f"Step {step.id} ({step.kind}): {step.title}. {step.description}\n"
        f"The step produces: {produces}\n"
        f"Columns available when this step runs: {compact_json(_columns_at(plan, step))}\n"
        f"Failed options and their last errors: {compact_json(failed)}"
    )
    return messages(SYSTEM, user)
