"""Model options are coded after every other option.

The model reads what earlier steps store in ctx, and the guard and the template request decide
what it must read from those writes. Coded all at once, a model option saw only the earlier
options' specs, and a spec in prose ("Set outcome = wb_overall_mean. Write to ctx['outcome']")
names no value, so a template that ignored the outcome choice passed and the decision had no
effect in any universe (marp_norms, 2a2d925). Coded after the others, the model sees their code.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.llm.gather import gather_cancelling

Result = tuple[str | None, int, str | None]
Work = Callable[[AnalysisPlan, Step, Option], Awaitable[Result]]


async def code_in_order(
    plan: AnalysisPlan, pending: list[tuple[Step, Option]], work: Work
) -> list[Result]:
    first = [(s, o) for s, o in pending if s.kind != "model"]
    later = [(s, o) for s, o in pending if s.kind == "model"]
    done = await gather_cancelling(work(plan, s, o) for s, o in first)
    staged = plan.model_copy(deep=True)
    for (step, option), (code, _, _) in zip(first, done, strict=True):
        if code is not None:
            staged.step(step.id).option(option.id).code = code
    rest = await gather_cancelling(work(staged, s, o) for s, o in later)
    found = dict(zip([(s.id, o.id) for s, o in [*first, *later]], [*done, *rest], strict=True))
    return [found[(s.id, o.id)] for s, o in pending]
