"""A model reads ctx['covariates'] whenever an earlier step writes it.

In an audit run (r_20261009T023828_e093b0) the judge left the adjustment step with one option,
ctx['covariates'] = [], so the model was rendered with a fixed empty list. The adversary then
proposed adjusting for client revenue, the confounder that turns the tool's effect to zero, and
the option was dropped because no model read the list. Reading it costs nothing when the list is
empty, so the default result is unchanged; an option that says it is unadjusted keeps its own list.
"""

from __future__ import annotations

from borges.analysis.code_guard_ctx import UNADJUSTED, ctx_writes
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import AnalysisPlan, Step


def earlier_writes_covariates(plan: AnalysisPlan, step: Step) -> bool:
    index = next(i for i, s in enumerate(plan.steps) if s.id == step.id)
    return any(
        "covariates" in ctx_writes(text)
        for earlier in plan.steps[:index]
        for option in earlier.options
        for text in (option.spec, option.code or "")
    )


def reading_ctx_covariates(
    spec: ModelSpecOutput, plan: AnalysisPlan, step: Step, intent: str
) -> ModelSpecOutput:
    if spec.covariates_from_ctx or UNADJUSTED.search(intent):
        return spec
    if not earlier_writes_covariates(plan, step):
        return spec
    return spec.model_copy(update={"covariates_from_ctx": True})
