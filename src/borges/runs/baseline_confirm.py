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

from borges.analysis.models import AnalysisPlan, AnalysisResult, Option
from borges.analysis.reference_writer import Fix, propose_fixes
from borges.analysis.row_key import row_key
from borges.garden.models import ReferenceCheck, Universe
from borges.gateway.errors import GatewayDenied
from borges.llm.client import LLMError
from borges.runs.baseline_dropped import located_difference
from borges.runs.baseline_fix_apply import closing_fixes
from borges.runs.baseline_lost import Lost, lost_defaults, withdraw_departures
from borges.runs.baseline_messages import (
    CONFIRMED_GAPS,
    DISAGREES,
    REPAIRED,
    UNCHECKED,
    UNRESOLVED,
)
from borges.runs.baseline_rebuild import REBUILT, rebuild_round
from borges.runs.baseline_reference import agreed_reference, describe, same_result
from borges.runs.pipeline_caveats import GAP_PREFIX
from borges.runtime.stage_checkpoints import CODED_KEY, coded_payload

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline

MAX_FIX_ROUNDS = 2
ERROR_CHARS = 200
RunBaseline = Callable[[dict[str, str]], Awaitable[Universe]]
Snapshot = dict[str, list[Option]]


def _snapshot(plan: AnalysisPlan) -> Snapshot:
    return {s.id: [o.model_copy(deep=True) for o in s.options] for s in plan.steps}


def _restore(plan: AnalysisPlan, saved: Snapshot) -> bool:
    dumped = {key: [o.model_dump() for o in options] for key, options in saved.items()}
    changed = dumped != {s.id: [o.model_dump() for o in s.options] for s in plan.steps}
    for step in plan.steps:
        step.options = [o.model_copy(deep=True) for o in saved[step.id]]
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
    fit = found.fits.get(found.agreed[1], {})
    return await _repair(pipeline, plan, baseline, rerun, (*found.agreed, fit), saved)


async def _repair(
    pipeline: Pipeline,
    plan: AnalysisPlan,
    baseline: Universe,
    rerun: RunBaseline,
    reference: tuple[AnalysisResult, str, dict[str, object]],
    saved: Snapshot,
) -> Universe:
    assert baseline.result is not None
    theirs, code, fit = reference
    resolved = getattr(pipeline, "resolved", None)
    data = getattr(resolved, "data", None)
    ours = describe(baseline.result)
    outcomes = pipeline.smoke.state.outcomes if pipeline.smoke is not None else {}
    lost = lost_defaults(pipeline.planned, plan, outcomes)
    applied: list[Fix] = []
    restored: list[Lost] = []
    current = baseline
    evidence: dict[str, object] | None = None
    for _ in range(MAX_FIX_ROUNDS):
        assert current.result is not None
        dropped = {k[0]: (v.option, v.error) for k, v in lost.items() if v not in restored}
        evidence = await located_difference(
            pipeline.executor, plan, data, row_key(plan.dataset), current, fit
        )
        try:
            fixes = await propose_fixes(
                pipeline.llm, plan, current.traces, current.result, theirs, code, dropped, evidence
            )
        except (LLMError, GatewayDenied):
            fixes = []
        if not fixes:
            break
        candidate, kept, brought_back = await closing_fixes(plan, fixes, lost, rerun, theirs)
        applied.extend(kept)
        restored.extend(brought_back)
        if candidate.result is None:
            break
        current = candidate
        if same_result(candidate.result, theirs):
            withdraw_departures(pipeline.caveats, plan, restored)
            pipeline.caveats.append(_repaired_note(plan, applied, ours, theirs))
            _save(pipeline, plan)
            return _confirmed(pipeline, "repaired", candidate)
    rebuilt = await rebuild_round(
        pipeline.llm, plan, current, (theirs, code), evidence, lost, rerun
    )
    if rebuilt is not None:
        candidate, kept, brought_back = rebuilt
        withdraw_departures(pipeline.caveats, plan, [*restored, *brought_back])
        pipeline.caveats.append(_repaired_note(plan, kept, ours, theirs, REBUILT))
        _save(pipeline, plan)
        return _confirmed(pipeline, "repaired", candidate)
    if _restore(plan, saved):
        current = await rerun(plan.default_choices())
    pipeline.search.reference = "disagrees"
    pipeline.caveats.append(DISAGREES.format(ours=ours, theirs=describe(theirs)))
    return current


def _repaired_note(
    plan: AnalysisPlan,
    applied: list[Fix],
    ours: str,
    theirs: AnalysisResult,
    template: str = REPAIRED,
) -> str:
    titles = list(dict.fromkeys(f"'{plan.step(f.step_id).title}'" for f in applied))
    why = "; ".join(dict.fromkeys(" ".join(f.problem.split())[:ERROR_CHARS] for f in applied))
    return template.format(ours=ours, theirs=describe(theirs), steps=", ".join(titles), why=why)


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
