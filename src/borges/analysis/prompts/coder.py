from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts import compact_json, messages

SYSTEM = """You write one small, correct Python module implementing a single analysis option.

Code contract:
- The code is complete Python source defining exactly one function.
- For steps of kind filter, transform or feature: `def apply(df, ctx)` returning a pandas \
DataFrame.
- For the step of kind model: `def estimate(df, ctx)` returning a dict with float keys \
"estimate", "ci_low", "ci_high", "p_value", an int "n", and optionally "extra": dict[str, float].
- Top-level `import` / `from` of these modules only: pandas, numpy, math, scipy, scipy.stats, \
statsmodels, statsmodels.api, statsmodels.formula.api. Any other top-level statement is \
rejected. No file, network or process access, no eval/exec, no dunder access.
- `ctx` is a JSON-serialisable dict that carries decisions forward; it may be mutated in \
place. Store only JSON-serialisable values (lists, numbers, strings).
- The code guard rejects subscripts whose key is built at run time. Never write \
`df[col + "_z"]` or `df[f"{col}_z"]`; write each column name as a plain string literal, or \
build new columns with `df.assign(**{name: values})` or `df.rename(columns=mapping)`.
- Be deterministic: any randomness uses a fixed seed.
- Use exact column names. Do not mutate the input frame in place unless copying first. Do \
not print. No comments.
- Implement exactly the option spec; do not add other analysis choices.

Return only JSON matching the requested schema, with the source in the `code` field."""


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


def build_messages(
    plan: AnalysisPlan, step: Step, option: Option, error: str | None
) -> list[dict[str, str]]:
    columns = [{"name": c.name, "dtype": c.dtype} for c in plan.dataset.columns]
    function = "estimate" if step.kind == "model" else "apply"
    parts = [
        f"Estimand: {plan.estimand}",
        f"Columns: {compact_json(columns)}",
        f"Earlier steps and their possible options (columns or ctx keys they create may "
        f"or may not exist depending on the option chosen): "
        f"{compact_json(_earlier_specs(plan, step))}",
        f"Current step: {step.id} ({step.kind}) {step.title}. {step.description}",
        f"Option {option.id}: {option.label}\nSpec: {option.spec}",
        f"Write `{function}(df, ctx)`.",
    ]
    if error is not None:
        parts.append(f"Your previous code:\n{option.code}\nIt failed with:\n{error}\nFix it.")
    return messages(SYSTEM, "\n\n".join(parts))
