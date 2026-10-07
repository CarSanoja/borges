"""The last repair of a starting point: every default step rewritten from the reference script.

fertility_vote on 7 October, run 37: the step-by-step code coded single women as 1 where the
analysis codes committed women as 1, which reverses the sign, and lost the two hand-set days; the
two independent scripts agreed on the published cell, and two rounds of targeted repairs proposed
an irrelevant change. When the targeted rounds fail, the repairer rewrites the default option of
every step from the reference script, keeping each step's role and products; the rewrite is kept
only if the chain then reproduces the reference, and the report says it was rewritten from it.
"""

from __future__ import annotations

from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.analysis.reference_writer import Fix, propose_fixes
from borges.garden.models import Universe
from borges.gateway.errors import GatewayDenied
from borges.llm.client import LLMClient, LLMError
from borges.runs.baseline_fix_apply import RunBaseline, closing_fixes
from borges.runs.baseline_lost import Lost
from borges.runs.baseline_reference import same_result

REBUILT = (
    "The step-by-step code of your analysis first gave {ours}; two independent implementations "
    "of it, each written as one script, gave {theirs}. Repairs of single steps did not close the "
    "gap, so the code of {steps} was rewritten from one of those implementations, and the "
    "starting point now matches them."
)


async def rebuild_round(
    llm: LLMClient,
    plan: AnalysisPlan,
    current: Universe,
    reference: tuple[AnalysisResult, str],
    evidence: dict[str, object] | None,
    lost: dict[tuple[str, str], Lost],
    rerun: RunBaseline,
) -> tuple[Universe, list[Fix], list[Lost]] | None:
    """The rerun, the fixes kept and the options restored, or None with the plan as it was."""
    assert current.result is not None
    theirs, code = reference
    try:
        fixes = await propose_fixes(
            llm, plan, current.traces, current.result, theirs, code, {}, evidence, rebuild=True
        )
    except (LLMError, GatewayDenied):
        return None
    if not fixes:
        return None
    candidate, kept, restored = await closing_fixes(plan, fixes, lost, rerun, theirs)
    if candidate.result is not None and same_result(candidate.result, theirs):
        return candidate, kept, restored
    return None
