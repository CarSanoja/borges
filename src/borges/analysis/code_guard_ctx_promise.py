"""ctx keys a spec promises, that a later step reads, and that the code never writes.

fertility_vote on 7 October, run 23: the relationship step's spec said "Write to
ctx['relationship_group_col'] = 'is_committed'", its code built the column and never wrote the
key, and every option of the model, which reads ctx['relationship_group_col'], failed with a
KeyError until the run failed. The spec guard held only the covariate list and the outcome to the
spec, because planners also promise keys nobody reads; a key a later step reads is held too.
"""

from __future__ import annotations

import ast

from borges.analysis.code_guard_ctx import COLUMN_KEYS, ctx_read_pattern, ctx_writes
from borges.analysis.code_guard_ctx_spec import SET_IN_SPEC, _written_keys
from borges.analysis.models import AnalysisPlan, Option, Step


def _later_texts(plan: AnalysisPlan, step: Step) -> list[str]:
    index = next((i for i, s in enumerate(plan.steps) if s.id == step.id), None)
    if index is None:
        return []
    later = plan.steps[index + 1 :]
    return [text for s in later for o in s.options for text in (o.spec, o.code or "")]


def read_promise_violations(code: str, plan: AnalysisPlan, step: Step, option: Option) -> list[str]:
    promised = {a or b for a, b in SET_IN_SPEC.findall(option.spec)} | set(ctx_writes(option.spec))
    promised -= COLUMN_KEYS
    if not promised:
        return []
    later = _later_texts(plan, step)
    read = sorted(k for k in promised if any(ctx_read_pattern(k).search(t) for t in later))
    if not read:
        return []
    try:
        written = _written_keys(ast.parse(code))
    except SyntaxError:
        return []
    if "*" in written:
        return []
    return [
        f"the option's spec sets ctx['{key}'] and a later step reads ctx['{key}'], but this code "
        f"never writes it, so that step fails; assign ctx['{key}'] as the spec says"
        for key in read
        if key not in written
    ]
