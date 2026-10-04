from __future__ import annotations

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate_exposure import MAX_LISTED_LEVELS, column_levels, is_text
from borges.analysis.models import AnalysisPlan, ColumnProfile, Option, Step
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.coder import _available_columns, _earlier_specs
from borges.analysis.scale_check import scale_instruction

SYSTEM = """\
You translate one regression option of an analysis plan into a structured model spec. Borges \
renders the spec into code with fixed, tested templates, so you never write code.

Return JSON with these fields:
- supported: true when the option is a single regression the templates express, otherwise false \
with the reason in `reason`.
- family: "ols", "logit" (binary outcome), "poisson", "quasipoisson" or "negbin" (count \
outcome). Use the family the option names: quasi-Poisson is "quasipoisson" (the Poisson estimate \
with standard errors scaled by the Pearson dispersion), never "negbin".
- outcome: the dependent column.
- exposure: the column whose coefficient is the estimate: the treatment, group or attribute the \
estimand is about, never the offset column and never the outcome.
- exposure_level: only when the exposure is a text column: the level coded 1, the treatment or the \
group the estimand puts first ("treatment minus control" means level "treatment"). With more than \
two levels the estimate compares that level with all the others together. Use a level exactly as \
listed. Leave it null for a numeric exposure; never invent a column for the dummy. When the \
option builds a 0/1 indicator from a text column, as treatment = (variant == 'treatment'), the \
exposure is that text column and exposure_level its level: the template builds the indicator.
- moderator: optional column; when set the estimate is the coefficient of the exposure x \
moderator interaction and both main effects are included.
- covariates: literal covariate columns; covariates_from_ctx: true when the option also uses the \
list an earlier step stored in ctx["covariates"]. Never repeat a column of that list in \
covariates: the covariate step chooses it, and a literal copy would keep it in every universe.
- offset_log: optional column whose log is the offset (count families only). The offset column may \
also be a covariate, never the exposure.
- cov_type: "nonrobust", "HC0", "HC1", "HC2", "HC3" or "cluster" (the one the option names); \
with "cluster" set `cluster` to the grouping \
column.
- standardize: columns to z-score before fitting (never the outcome of logit, poisson, negbin); \
when the decision rule asks for a standardised coefficient, z-score the outcome, the exposure \
and any moderator.
- report: "coefficient", "odds_ratio" (logit only), "rate_ratio" (count families only) or \
"marginal_effect" (logit only, no moderator): the average marginal effect of the exposure on the \
probability scale, the right report when the decision rule is a difference in proportions.

Use exact column names from the list of available columns. Categorical covariates are \
dummy-encoded automatically. Set supported to false for anything else: mixed or multilevel \
models, GEE, t-tests, difference in proportions, bootstrap, nonparametric tests, weights, \
splines, outcome transformations, fixed effects written as dummies of a column you cannot list, \
or a model that reads ctx values other than the covariate list. Never refuse for any other \
reason: translate the exposure the option names even if you would choose another (a validator \
checks it against the estimand), and any available column, numeric or text, can be the cluster.

Return only JSON matching the requested schema."""


def _column_entry(column: ColumnProfile) -> dict[str, object]:
    entry: dict[str, object] = {
        "name": column.name,
        "dtype": column.dtype,
        "unique": column.n_unique,
    }
    if is_text(column) and 2 <= column.n_unique <= MAX_LISTED_LEVELS:
        entry["levels"] = column_levels(column)
    return entry


def build_spec_messages(plan: AnalysisPlan, step: Step, option: Option) -> list[dict[str, str]]:
    columns = [_column_entry(c) for c in plan.dataset.columns]
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


def correction(spec: ModelSpecOutput, problems: list[str]) -> list[dict[str, str]]:
    return [
        {"role": "assistant", "content": spec.model_dump_json()},
        {
            "role": "user",
            "content": "That spec cannot be rendered: "
            + "; ".join(problems)
            + ". Return a corrected spec for the same option, or supported false with a reason.",
        },
    ]
