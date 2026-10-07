"""Check the starting point against independent implementations of the user's analysis.

On a run from the user's own analysis, a second model writes the whole analysis as one script, twice
and independently, and each script is run on the raw data. The baseline is what is under test, so
it never votes: two scripts that agree with each other are the reference, and a third is written
when the first two disagree or one fails. A reference equal to the baseline confirms it; a
different one means the step-by-step code departs from the analysis, and the steps that depart are
repaired against the reference, twice at most. Each outcome is reported; a repair that does not
reach the reference is undone. Run 14 of fertility_vote on 7 October is why the baseline does not
vote: the first script was right, the second copied the baseline's mistake (two participants
dropped), and a two-of-three vote counting the baseline confirmed the wrong starting point.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.analysis.reference_writer import Fix, propose_fixes
from borges.garden.models import ReferenceCheck, Universe
from borges.gateway.errors import GatewayDenied
from borges.llm.client import LLMError
from borges.runs.baseline_reference import agreed_reference, describe, same_result
from borges.runs.pipeline_caveats import GAP_PREFIX
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
    "The starting point could not be confirmed: the step-by-step code gives {ours}, and no two "
    "independent implementations of your analysis agreed with each other ({listed})."
)
CONFIRMED_GAPS = (
    "Before the code was written, a comparison of the plan with your analysis listed {n} possible "
    "difference{s}; an independent implementation of your analysis gives the same estimate, "
    "interval and n as the starting point, so on this data {they} not change the original result."
)
UNCHECKED = (
    "The starting point was not checked against an independent implementation of your analysis, "
    "which could not be run ({error})."
)


Snapshot = dict[tuple[str, str], tuple[str | None, str]]


def _snapshot(plan: AnalysisPlan) -> Snapshot:
    return {(s.id, o.id): (o.code, o.spec) for s in plan.steps for o in s.options}


def _restore(plan: AnalysisPlan, saved: Snapshot) -> bool:
    changed = saved != _snapshot(plan)
    for step in plan.steps:
        for option in step.options:
            option.code, option.spec = saved[(step.id, option.id)]
    return changed


async def confirm_baseline(
    pipeline: Pipeline, plan: AnalysisPlan, baseline: Universe, rerun: RunBaseline
) -> Universe:
    """A check that cannot finish leaves the run as it was and says so; it never fails it."""
    if not plan.analysis or baseline.result is None or pipeline.restored:
        return baseline
    if pipeline.executor is None:
        return baseline
    saved = _snapshot(plan)
    try:
        return await _confirm(pipeline, plan, baseline, rerun, saved)
    except (LLMError, GatewayDenied) as exc:
        pipeline.search.reference = "unchecked"
        pipeline.caveats.append(UNCHECKED.format(error=" ".join(str(exc).split())[:ERROR_CHARS]))
        if _restore(plan, saved):
            return await rerun(plan.default_choices())
        return baseline


async def _confirm(
    pipeline: Pipeline, plan: AnalysisPlan, baseline: Universe, rerun: RunBaseline, saved: Snapshot
) -> Universe:
    assert baseline.result is not None
    ours = baseline.result
    found = await agreed_reference(pipeline.llm, pipeline.executor, plan)
    pipeline.search.reference_results = [result for result, _ in found.results]
    if found.agreed is None and not found.results:
        pipeline.search.reference = "unchecked"
        error = " ".join(found.errors[0].split())[:ERROR_CHARS] if found.errors else "no result"
        pipeline.caveats.append(UNCHECKED.format(error=error))
        return baseline
    if found.agreed is None:
        pipeline.search.reference = "unresolved"
        listed = "; ".join(describe(result) for result, _ in found.results)
        pipeline.caveats.append(UNRESOLVED.format(ours=describe(ours), listed=listed))
        return baseline
    if same_result(ours, found.agreed[0]):
        return _confirmed(pipeline, "agrees", baseline)
    return await _repair(pipeline, plan, baseline, rerun, found.agreed, saved)


async def _repair(
    pipeline: Pipeline,
    plan: AnalysisPlan,
    baseline: Universe,
    rerun: RunBaseline,
    reference: tuple[AnalysisResult, str],
    saved: Snapshot,
) -> Universe:
    assert baseline.result is not None
    theirs, code = reference
    ours = describe(baseline.result)
    applied: list[Fix] = []
    current = baseline
    for _ in range(MAX_FIX_ROUNDS):
        assert current.result is not None
        try:
            fixes = await propose_fixes(
                pipeline.llm, plan, current.traces, current.result, theirs, code
            )
        except (LLMError, GatewayDenied):
            fixes = []
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
            pipeline.caveats.append(_repaired_note(plan, applied, ours, theirs))
            _save(pipeline, plan)
            return _confirmed(pipeline, "repaired", candidate)
    if _restore(plan, saved):
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


def _confirmed(pipeline: Pipeline, outcome: ReferenceCheck, baseline: Universe) -> Universe:
    pipeline.search.reference = outcome
    gaps = [c for c in pipeline.caveats if c.startswith(GAP_PREFIX)]
    if gaps:
        pipeline.caveats[:] = [c for c in pipeline.caveats if not c.startswith(GAP_PREFIX)]
        plural = len(gaps) > 1
        pipeline.caveats.append(
            CONFIRMED_GAPS.format(
                n=len(gaps), s="s" if plural else "", they="they do" if plural else "it does"
            )
        )
    return baseline


def _save(pipeline: Pipeline, plan: AnalysisPlan) -> None:
    notes = pipeline.smoke.state.notes if pipeline.smoke is not None else []
    pipeline.checkpoint(CODED_KEY, coded_payload(plan, pipeline.judged, pipeline.coding, notes))
