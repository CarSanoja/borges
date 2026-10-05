from __future__ import annotations

import re

from borges.analysis.code_guard_rules import ALLOWED_IMPORTS
from borges.analysis.harness import RESULT_KEYS
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.coder_recode import recode_instruction
from borges.analysis.prompts.notes import describe_column_notes
from borges.analysis.scale_check import scale_instruction

ALLOWLIST = ", ".join(sorted(ALLOWED_IMPORTS))
_REJECTED_IMPORT = re.compile(r"import of '([\w.]+)' is not allowed")
_ALTERNATIVES = "use statsmodels or numpy"


def _result_contract(kind: str) -> str:
    if kind != "model":
        return "def apply(df, ctx) returning a pandas DataFrame."
    keys = ", ".join(f'"{key}"' for key in RESULT_KEYS)
    return (
        f"def estimate(df, ctx) returning a dict with exactly the keys {keys} (and optionally "
        '"extra": dict[str, float]). "estimate", "ci_low", "ci_high" and "p_value" are floats '
        'with "ci_low" < "ci_high" (a 95% interval that is not degenerate), "estimate" inside '
        '[ci_low, ci_high] and "p_value" in [0, 1], the two-sided p-value for the null of no '
        'effect; "n" is a positive int, the number of rows used.'
    )


def contract_reminder(kind: str) -> str:
    return f"Contract: {_result_contract(kind)} Allowed imports, and only these: {ALLOWLIST}."


def rejected_import_hints(error: str) -> list[str]:
    roots: list[str] = []
    for module in _REJECTED_IMPORT.findall(error):
        root = module.split(".")[0]
        if root not in roots:
            roots.append(root)
    return [f"{root} is not available; {_ALTERNATIVES}" for root in roots]


_SYSTEM_TEMPLATE = """\
You write one small, correct Python module implementing a single analysis option.

Code contract:
- The code is complete Python source defining exactly one function.
- For steps of kind filter, transform or feature: `def apply(df, ctx)` returning a pandas \
DataFrame.
- For the step of kind model: `def estimate(df, ctx)` returning a dict with float keys \
"estimate", "ci_low", "ci_high", "p_value", an int "n", and optionally "extra": dict[str, float].
- Top-level `import` / `from` of these modules only: __ALLOWLIST__. Any other top-level \
statement is rejected. No file, network or process access, no eval/exec, no dunder access.
- `ctx` is a JSON-serialisable dict that carries decisions forward; it may be mutated in \
place. Store only JSON-serialisable values (lists, numbers, strings). Read data columns from \
`df` by their literal names; ctx holds only what an earlier step stored in it (for example \
ctx["covariates"]), so never look a column name up in ctx (`df["outcome"]`, not \
`df[ctx["outcome"]]`).
- A row whose input columns are missing stays missing in every column built from them: a \
comparison with a missing value is False and fillna invents a value, so `(x >= cut).astype(int)` \
puts every missing row in group 0. Build the column, then blank those rows: \
`out.loc[out[["a", "b"]].isna().all(axis=1), "new"] = float("nan")`. numpy reductions \
(np.cov, np.median, np.mean) return NaN when a value is missing: compute them on the complete \
rows only. Fill missing values only when the option says it imputes them. In a model step, \
drop the rows where a column you compare or transform is missing before building anything from \
it, and report n as the rows fitted.
- Keys built at run time, such as `df[col + "_z"]` or `df[f"{col}_z"]`, are allowed only on \
the data frame itself (named df, out, data or frame); on any other object the code guard \
rejects them, so write the key as a plain string literal there, or build new columns with \
`df.assign(**{name: values})`.
- For the step of kind model: compute standard errors, confidence intervals and p-values with \
statsmodels (the formula API or the sm.stats functions), never by hand-written formulas. A \
hand-computed standard error that is wrong makes the whole analysis wrong. Take p-values and \
confidence intervals from the fitted result (`pvalues`, `conf_int()`, or exp of them for \
ratios), never recompute them from a hand-written distribution (`sm.norm`, `sm.t` and the \
like do not exist).
- A model step never selects rows by value: inside estimate() do not write `df[df["x"] == 1]`, \
`.loc[<comparison>]`, `.query(...)` or an `isin`/`between` mask. The only rows a model may \
drop are incomplete ones (`dropna`, or a mask that only tests isna/notna); excluding or keeping \
records by value is a decision of a filter step and the code guard rejects it.
- Return estimate, ci_low and ci_high on the natural scale of the estimator: a difference in \
proportions as a proportion (-0.0014, never -0.14), a ratio as a ratio, a coefficient as fitted. \
Borges converts units itself; never multiply by 100.
- Never drop columns: filters only drop rows, transforms and features keep every input column \
and add or change columns. The one exception is a step whose spec aggregates rows (one row per \
group, e.g. per user): it returns the group key, the grouping variables the later steps need \
(such as the treatment indicator) and the names this step must create. Keep the direction and \
coding of every variable. Never swap or recode groups (a treatment indicator stays 1 for \
treatment). Orient a PCA or factor score by its correlation with the plain mean of its items: \
`if np.corrcoef(score, items.mean(axis=1))[0, 1] < 0: score = -score`. Never orient by the sign \
of the scores' mean, which is zero. Write `pd.get_dummies(..., dtype=float)`: the default bool \
dummies cannot hold standardised values.
- For the step of kind model: start with complete cases, `data = df.dropna(subset=[...])` over \
every column the model uses (outcome, predictors, offsets, weights, cluster or group columns), \
build the model, its groups and its weights from that same frame, and return n = len(data). \
statsmodels fails on missing values, and cluster groups must have the same length as the rows \
used.
- When a model step reads its covariate list from ctx (or any list you do not know in advance), \
other steps may have added string or categorical covariates: encode every non-numeric covariate \
with `pd.get_dummies(..., drop_first=True, dtype=float)` before fitting and never pass raw \
strings to the estimator.
- Be deterministic: any randomness uses a fixed seed.
- Use exact column names. Do not mutate the input frame in place unless copying first. Do \
not print. No comments.
- Implement exactly the option spec; do not add other analysis choices.

Return only JSON matching the requested schema, with the source in the `code` field."""
SYSTEM = _SYSTEM_TEMPLATE.replace("__ALLOWLIST__", ALLOWLIST)


def _earlier_specs(plan: AnalysisPlan, step: Step) -> list[dict[str, object]]:
    earlier: list[dict[str, object]] = []
    for prior in plan.steps:
        if prior.id == step.id:
            break
        earlier.append(
            {
                "step": prior.id,
                "kind": prior.kind,
                "options": {o.id: o.spec for o in prior.options},
            }
        )
    return earlier


def _available_columns(plan: AnalysisPlan, step: Step) -> list[str]:
    names = [c.name for c in plan.dataset.columns]
    for prior in plan.steps:
        if prior.id == step.id:
            break
        names.extend(n for n in prior.produces if n not in names)
    return names


def _step_requirements(plan: AnalysisPlan, step: Step) -> list[str]:
    available = ", ".join(_available_columns(plan, step))
    parts = [f"Columns available when this step runs: {available}"]
    if step.produces:
        names = ", ".join(step.produces)
        parts.append(
            f"This step must create: {names}, with exactly these names for every option. An "
            "option that changes nothing still writes them, as an unchanged copy of the column "
            "they are built from, or as 0 for an indicator that none of its rows has."
        )
    if step.kind == "model":
        parts.append(
            "Read only the columns available when this step runs; do not read any other name."
        )
    return parts


def build_messages(
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    error: str | None,
    errors: list[str] | None = None,
) -> list[dict[str, str]]:
    columns = [{"name": c.name, "dtype": c.dtype} for c in plan.dataset.columns]
    function = "estimate" if step.kind == "model" else "apply"
    notes = describe_column_notes(plan.dataset)
    parts = [
        f"Estimand: {plan.estimand}",
        f"Columns: {compact_json(columns)}",
        *([notes] if notes else []),
        *_step_requirements(plan, step),
        f"Earlier steps and their possible options (columns or ctx keys they create may "
        f"or may not exist depending on the option chosen): "
        f"{compact_json(_earlier_specs(plan, step))}",
        f"Current step: {step.id} ({step.kind}) {step.title}. {step.description}",
        f"Option {option.id}: {option.label}\nSpec: {option.spec}",
        f"Write `{function}(df, ctx)`.",
        *([scale_instruction(plan.decision_rule)] if step.kind == "model" else []),
        contract_reminder(step.kind),
    ]
    if errors:
        parts.append(recode_instruction(errors))
    elif error is not None:
        hints = "".join(f"\n{hint}." for hint in rejected_import_hints(error))
        parts.append(
            f"Your previous code:\n{option.code}\nIt failed with:\n{error}{hints}\nFix it."
        )
    return messages(SYSTEM, "\n\n".join(parts))
