from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.coder import _available_columns, _earlier_specs
from borges.analysis.scale_check import scale_instruction

SYSTEM = """\
You translate one regression option of an analysis plan into a structured model spec. Borges \
renders the spec into code with fixed, tested templates, so you never write code.

Return JSON with these fields:
- supported: true when the option is a single regression the templates express, otherwise false \
with the reason in `reason`.
- family: "ols", "logit" (binary outcome), "poisson" or "negbin" (count outcome).
- outcome: the dependent column.
- exposure: the column whose coefficient is the estimate.
- moderator: optional column; when set the estimate is the coefficient of the exposure x \
moderator interaction and both main effects are included.
- covariates: literal covariate columns; covariates_from_ctx: true when the option also uses the \
list an earlier step stored in ctx["covariates"].
- offset_log: optional column whose log is the offset (poisson and negbin only).
- cov_type: "nonrobust", "HC0", "HC1", "HC2", "HC3" or "cluster" (the one the option names); \
with "cluster" set `cluster` to the grouping \
column.
- standardize: columns to z-score before fitting (never the outcome of logit, poisson, negbin).
- report: "coefficient", "odds_ratio" (logit only) or "rate_ratio" (poisson and negbin only).

Use exact column names from the list of available columns. Categorical covariates are \
dummy-encoded automatically. Set supported to false for anything else: mixed or multilevel \
models, GEE, t-tests, difference in proportions, bootstrap, nonparametric tests, weights, \
splines, outcome transformations, fixed effects written as dummies of a column you cannot list, \
or a model that reads ctx values other than the covariate list.

Return only JSON matching the requested schema."""


def build_spec_messages(plan: AnalysisPlan, step: Step, option: Option) -> list[dict[str, str]]:
    columns = [
        {"name": c.name, "dtype": c.dtype, "unique": c.n_unique} for c in plan.dataset.columns
    ]
    parts = [
        f"Estimand: {plan.estimand}",
        f"Columns: {compact_json(columns)}",
        f"Columns available when this step runs: {', '.join(_available_columns(plan, step))}",
        f"Earlier steps and their possible options: {compact_json(_earlier_specs(plan, step))}",
        f"Current step: {step.id} ({step.kind}) {step.title}. {step.description}",
        f"Option {option.id}: {option.label}\nSpec: {option.spec}",
        scale_instruction(plan.decision_rule),
        "Translate this option into the model spec, or return supported false with a reason.",
    ]
    return messages(SYSTEM, "\n\n".join(parts))
