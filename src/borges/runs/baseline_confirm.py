"""Check the starting point against independent implementations of the user's analysis.

On a run from the user's own analysis, a second model writes the whole analysis as one script and
it is run on the raw data. If its result matches the step-by-step baseline, the starting point is
confirmed. If not, a second script breaks the tie: when it sides with the baseline, the first
script was wrong; when the two scripts agree with each other, the step-by-step code is wrong, and
the steps that depart from the analysis are repaired against it, twice at most. Each outcome is
reported; a repair that breaks the baseline is undone. See `analysis/reference_writer.py`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.analysis.reference_writer import Fix, propose_fixes
from borges.garden.models import Universe
from borges.runs.baseline_reference import describe, reference_result, same_result
from borges.runtime.stage_checkpoints import CODED_KEY, coded_payload

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline

MAX_FIX_ROUNDS = 2
ERROR_CHARS = 200
RunBaseline = Callable[[dict[str, str]], Awaitable[Universe]]
REPAIRED = (
    "The step-by-step code of your analysis first gave {ours}; two independent implementations "
    "of it, each written as one script, gave {theirs}. The code of {steps} was repaired ({why}) "
    "and the starting point now matches them."
)
DISAGREES = (
    "The starting point does not match your analysis as two independent implementations of it "
    "compute it: the step-by-step code gives {ours} and both implementations give {theirs}; "
    "repairing the steps did not close the gap. Read the original result with care."
)
UNRESOLVED = (
    "The starting point could not be confirmed: the step-by-step code gives {ours} and two "
    "independent implementations of your analysis gave {first} and {second}."
)
UNCHECKED = (
    "The starting point was not checked against an independent implementation of your analysis, "
    "which could not be run ({error})."
)


async def confirm_baseline(
    pipeline: Pipeline, plan: AnalysisPlan, baseline: Universe, rerun: RunBaseline
) -> Universe:
    executor = pipeline.executor
    if not plan.analysis or baseline.result is None or pipeline.restored or executor is None:
        return baseline
    ours = baseline.result
    first, code = await reference_result(pipeline.llm, executor, plan, 1)
    if first is None:
        pipeline.search.reference = "unchecked"
        pipeline.caveats.append(UNCHECKED.format(error=" ".join(code.split())[:ERROR_CHARS]))
        return baseline
    if same_result(ours, first):
        pipeline.search.reference = "agrees"
        return baseline
    second, _ = await reference_result(pipeline.llm, executor, plan, 2)
    if second is not None and same_result(ours, second):
        pipeline.search.reference = "agrees"
        return baseline
    if second is None or not same_result(first, second):
        pipeline.search.reference = "unresolved"
        pipeline.caveats.append(
            UNRESOLVED.format(
                ours=describe(ours),
                first=describe(first),
                second=describe(second) if second is not None else "no result",
            )
        )
        return baseline
    return await _repair(pipeline, plan, baseline, rerun, first, code)


async def _repair(
    pipeline: Pipeline,
    plan: AnalysisPlan,
    baseline: Universe,
    rerun: RunBaseline,
    theirs: AnalysisResult,
    code: str,
) -> Universe:
    assert baseline.result is not None
    ours = describe(baseline.result)
    saved = {(s.id, o.id): (o.code, o.spec) for s in plan.steps for o in s.options}
    applied: list[Fix] = []
    current = baseline
    for _ in range(MAX_FIX_ROUNDS):
        assert current.result is not None
        fixes = await propose_fixes(
            pipeline.llm, plan, current.traces, current.result, theirs, code
        )
        if not fixes:
            break
        for fix in fixes:
            option = plan.step(fix.step_id).option(fix.option_id)
            option.code = fix.code
            option.spec = fix.spec or option.spec
        applied.extend(fixes)
        candidate = await rerun(plan.default_choices())
        if candidate.result is None:
            break
        current = candidate
        if same_result(candidate.result, theirs):
            pipeline.search.reference = "repaired"
            pipeline.caveats.append(_repaired_note(plan, applied, ours, theirs))
            _save(pipeline, plan)
            return candidate
    if applied:
        for step in plan.steps:
            for option in step.options:
                option.code, option.spec = saved[(step.id, option.id)]
        current = await rerun(plan.default_choices())
    pipeline.search.reference = "disagrees"
    pipeline.caveats.append(DISAGREES.format(ours=ours, theirs=describe(theirs)))
    return current


def _repaired_note(
    plan: AnalysisPlan, applied: list[Fix], ours: str, theirs: AnalysisResult
) -> str:
    titles = list(dict.fromkeys(f"'{plan.step(f.step_id).title}'" for f in applied))
    why = "; ".join(dict.fromkeys(" ".join(f.problem.split())[:ERROR_CHARS] for f in applied))
    return REPAIRED.format(ours=ours, theirs=describe(theirs), steps=", ".join(titles), why=why)


def _save(pipeline: Pipeline, plan: AnalysisPlan) -> None:
    notes = pipeline.smoke.state.notes if pipeline.smoke is not None else []
    pipeline.checkpoint(CODED_KEY, coded_payload(plan, pipeline.judged, pipeline.coding, notes))
