"""The ctx key that every option of a step writes, declared as what the step produces.

In the teaching_ratings runs of 6 Oct the planner left produces empty on a covariate step whose
options all read "Write [...] to ctx['covariates']". Both retries returned the same plan, so the
shortfall cost two planner calls and was never fixed. A key every option writes is what the
step produces, and that needs no model to say.
"""

from __future__ import annotations

import re

from borges.analysis.planner_products import PRODUCING_KINDS
from borges.analysis.schemas import PlannedStep, PlannerOutput

CTX_KEY = re.compile(r"""ctx\[\s*["']([A-Za-z_]\w*)["']\s*\]""")
ROW_WRITE = re.compile(
    r"""ctx\[\s*["']([A-Za-z_]\w*)["']\s*\]\s*=\s*(?:np\.where\(|df\[|df\.\w+\[|\(?df\[)"""
)
CTX_ASSIGN = re.compile(r"""ctx\[\s*["']([A-Za-z_]\w*)["']\s*\]\s*=(?!=)\s*([^;\n]+)""")
QUOTED = re.compile(r"""(["']).*?\1""")
PER_ROW_VALUE = re.compile(r"[<>]=?|==|\.dt\.|\bdf\[|np\.where\(")
STORED = re.compile(
    r"""\b(?:store|stores|write|writes|save|saves|put|puts|keep|keeps)\s+([A-Za-z_]\w*)\s+"""
    r"""(?:in|to|into)\s+ctx\[\s*["']([A-Za-z_]\w*)["']\s*\](?!\s+as\s+["'])""",
    re.IGNORECASE,
)


def ctx_keys_in(spec: str) -> set[str]:
    return set(CTX_KEY.findall(spec))


def with_ctx_products(out: PlannerOutput) -> PlannerOutput:
    steps = []
    for step in out.steps:
        if step.kind in PRODUCING_KINDS and not step.produces:
            shared = set.intersection(*(ctx_keys_in(o.spec) for o in step.options))
            if shared:
                step = step.model_copy(update={"produces": sorted(shared)})
        steps.append(step)
    return out.model_copy(update={"steps": steps})


def stored_rows(spec: str) -> list[str]:
    """ctx keys a spec fills with a quantity it computes per row, written as code or as prose
    ("cycle_day = 28 - days_to_onset; ... store cycle_day in ctx['cycle_day']")."""
    keys = ROW_WRITE.findall(spec)
    for key, value in CTX_ASSIGN.findall(spec):
        if PER_ROW_VALUE.search(QUOTED.sub("", value)) and key not in keys:
            keys.append(key)
    for name, key in STORED.findall(spec):
        computed = re.search(rf"\b{re.escape(name)}\s*=(?!=)", spec)
        if computed and not is_column(spec, name) and key not in keys:
            keys.append(key)
    return keys


def is_column(spec: str, name: str) -> bool:
    quoted = rf"""["']{re.escape(name)}["']"""
    return bool(
        re.search(rf"\bcolumns?\s+(?:{quoted}|{re.escape(name)}\b)", spec, re.IGNORECASE)
        or re.search(rf"df\[\s*{quoted}\s*\]", spec)
    )


def ctx_row_shortfall(steps: list[PlannedStep]) -> str | None:
    """An option that stores a per-row array in ctx: a later step that drops rows reads it out
    of line with the rows it keeps (fert9 on 7 Oct coded every row single this way, and on the
    published-analysis probe of 7 Oct a filter kept the cycle day in ctx and the coder could only
    store an empty list there)."""
    found = [
        f"{s.id}.{o.id} (ctx['{key}'])"
        for s in steps
        for o in s.options
        for key in stored_rows(o.spec)
    ]
    if not found:
        return None
    return (
        "These options store one value per row in ctx, which falls out of line with the rows as "
        f"soon as a later step drops some: {', '.join(found)}. Write a per-row value as a column "
        "of df and list it in produces; keep ctx for run-level values such as the covariate list. "
        "A filter only drops rows and cannot add a column, so a quantity a filter selects on is "
        "computed by a feature step placed before the filter, which then filters on that column."
    )
