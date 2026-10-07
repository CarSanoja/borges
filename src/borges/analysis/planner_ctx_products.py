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


def ctx_row_shortfall(steps: list[PlannedStep]) -> str | None:
    """An option that stores a per-row array in ctx: a later step that drops rows reads it out
    of line with the rows it keeps (fert9 on 7 Oct coded every row single this way)."""
    found = [
        f"{s.id}.{o.id} (ctx['{key}'])"
        for s in steps
        for o in s.options
        for key in ROW_WRITE.findall(o.spec)
    ]
    if not found:
        return None
    return (
        "These options store one value per row in ctx, which falls out of line with the rows as "
        f"soon as a later step drops some: {', '.join(found)}. Write a per-row value as a column "
        "of df and list it in produces; keep ctx for run-level values such as the covariate list."
    )
