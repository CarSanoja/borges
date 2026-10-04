from __future__ import annotations

import ast
import re

from borges.analysis.code_guard_ctx import varying_ctx_keys
from borges.analysis.code_guard_produces import unused_products
from borges.analysis.models import AnalysisPlan, ColumnProfile, Step
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.coder import _available_columns

TEXT_DTYPES = ("object", "str", "string", "category")
ERROR_CHARS = 600
OBSERVED = re.compile(r"columns available \((\d+)\): (\[[^\]]*\])")

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


def observed_columns(errors: list[str]) -> list[str] | None:
    for error in errors:
        for count, listed in OBSERVED.findall(error or ""):
            try:
                names = ast.literal_eval(listed)
            except (ValueError, SyntaxError):
                continue
            if isinstance(names, list) and len(names) == int(count):
                return [str(name) for name in names]
    return None


def _columns_seen(plan: AnalysisPlan, step: Step, observed: list[str]) -> list[dict[str, object]]:
    known = {str(c["name"]): c for c in _columns_at(plan, step)}
    return [known.get(name, {"name": name}) for name in observed]


def _reads(plan: AnalysisPlan, step: Step) -> str:
    if step.kind != "model":
        return ""
    lines = [
        f"Every option must read ctx['{key}'], set differently by the earlier step '{title}', "
        "and use it as that step intends.\n"
        for key, title in sorted(varying_ctx_keys(plan, step).items())
    ]
    lines += [
        f"An option that needs what the earlier step '{title}' builds must read "
        f"{', '.join(names)}, never rebuild it from the raw columns.\n"
        for title, (names, _, _) in sorted(unused_products(plan, step).items())
    ]
    return "".join(lines)


def build_replan_messages(
    plan: AnalysisPlan, step: Step, failures: list[tuple[str, str, str, str]]
) -> list[dict[str, str]]:
    failed = [
        {"id": oid, "label": label, "spec": spec, "error": (error or "unknown")[:ERROR_CHARS]}
        for oid, label, spec, error in failures
    ]
    produces = ", ".join(step.produces) or "nothing"
    observed = observed_columns([error for *_, error in failures])
    columns = (
        f"Columns available when this step runs: {compact_json(_columns_at(plan, step))}\n"
        if observed is None
        else "Columns this step saw on the sample (an earlier step dropped every other column, so "
        f"no option may use one): {compact_json(_columns_seen(plan, step, observed))}\n"
    )
    user = (
        f"Estimand: {plan.estimand}\n"
        f"Decision rule: {compact_json(plan.decision_rule)}\n"
        f"Step {step.id} ({step.kind}): {step.title}. {step.description}\n"
        f"The step produces: {produces}\n"
        f"{columns}"
        f"{_reads(plan, step)}"
        f"Failed options and their last errors: {compact_json(failed)}"
    )
    return messages(SYSTEM, user)
