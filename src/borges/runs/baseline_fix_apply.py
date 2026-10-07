"""Apply the repairer's fixes, and keep only the ones that close the gap.

fertility_vote on 7 October, a replay of run 28's repair with the row evidence: the repairer fixed
the cycle-day step exactly (the hand-set days were written before the whole column), and in the
same answer replaced the window filter's code with the cycle-day code. Applied together, the
filter no longer filtered and the round failed, so the right fix was undone with the wrong one.
When the whole set does not reach the reference, each fix is tried alone; reruns run code in the
sandbox and call no model.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.models import AnalysisPlan, AnalysisResult, Option
from borges.analysis.reference_writer import Fix
from borges.garden.models import Universe
from borges.runs.baseline_lost import Lost, restore
from borges.runs.baseline_reference import same_result

RunBaseline = Callable[[dict[str, str]], Awaitable[Universe]]
Options = dict[str, list[Option]]


def _options(plan: AnalysisPlan) -> Options:
    return {s.id: [o.model_copy(deep=True) for o in s.options] for s in plan.steps}


def _put_back(plan: AnalysisPlan, saved: Options) -> None:
    for step in plan.steps:
        step.options = [o.model_copy(deep=True) for o in saved[step.id]]


def apply_fixes(
    plan: AnalysisPlan, fixes: list[Fix], lost: dict[tuple[str, str], Lost]
) -> list[Lost]:
    restored: list[Lost] = []
    for fix in fixes:
        step = plan.step(fix.step_id)
        if all(o.id != fix.option_id for o in step.options):
            if (fix.step_id, fix.option_id) in lost:
                restore(plan, lost[(fix.step_id, fix.option_id)], fix.code, fix.spec)
                restored.append(lost[(fix.step_id, fix.option_id)])
            continue
        option = step.option(fix.option_id)
        option.code = fix.code
        option.spec = fix.spec or option.spec
    return restored


async def closing_fixes(
    plan: AnalysisPlan,
    fixes: list[Fix],
    lost: dict[tuple[str, str], Lost],
    rerun: RunBaseline,
    theirs: AnalysisResult,
) -> tuple[Universe, list[Fix], list[Lost]]:
    """The rerun after the fixes, the fixes it kept and the lost options they restored. With no
    fix that reaches the reference, the whole set stays applied, as the repairer proposed it."""
    start = _options(plan)
    restored = apply_fixes(plan, fixes, lost)
    together = await rerun(plan.default_choices())
    if len(fixes) == 1 or (together.result is not None and same_result(together.result, theirs)):
        return together, fixes, restored
    for fix in fixes:
        _put_back(plan, start)
        alone = apply_fixes(plan, [fix], lost)
        candidate = await rerun(plan.default_choices())
        if candidate.result is not None and same_result(candidate.result, theirs):
            return candidate, [fix], alone
    _put_back(plan, start)
    return together, fixes, apply_fixes(plan, fixes, lost)
